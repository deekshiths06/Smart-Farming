"""Genuine image-classification inference for AI Crop Disease Identification.

This module wraps a real, pre-trained ONNX image classifier - CropGuard, a
ResNet50 fine-tuned on the PlantVillage dataset (38 classes across 14 crops) -
and runs it on uploaded leaf photographs. Nothing here is simulated: every
prediction is the actual output of the model's forward pass.

Coverage is deliberately narrow and explicit:

- only the 14 crops and 38 conditions the model was trained on are offered;
- a crop the model does not know is rejected before any inference runs;
- a prediction whose crop does not match the crop the farmer selected is
  reported as a mismatch, not presented as a diagnosis;
- a low-confidence prediction is reported as unreliable.

The model was trained on single leaves photographed against plain backgrounds
(the PlantVillage protocol). It has NOT been validated on field photographs and
does not provide treatment or chemical recommendations. ``onnxruntime`` and
``Pillow`` are imported lazily so the rest of the application still starts when
the optional ML extras are absent; callers get a clear ``ModelUnavailable``
instead.
"""

from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings

MODEL_NAME = "CropGuard ResNet50 (PlantVillage)"
MODEL_VERSION = "1.0.0"
MODEL_FILENAME = "cropguard.onnx"
CLASSES_FILENAME = "classes.json"

# Result statuses. A row is only ever written with one of these.
STATUS_IDENTIFIED = "identified"
STATUS_HEALTHY = "healthy"
STATUS_LOW_CONFIDENCE = "low_confidence"
STATUS_CROP_MISMATCH = "crop_mismatch"

ASSESSMENT_STATUSES: tuple[str, ...] = (
    STATUS_IDENTIFIED,
    STATUS_HEALTHY,
    STATUS_LOW_CONFIDENCE,
    STATUS_CROP_MISMATCH,
)

# Preprocessing must match training (documented by the model authors):
# resize the short side to 256, centre-crop 224, scale to [0,1], normalise with
# the ImageNet mean/std, NCHW.
RESIZE_SHORT_SIDE = 256
INPUT_SIZE = 224
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

# Temperature scaling fitted by the model authors on the validation split
# (T = 0.591). The published ONNX graph emits raw logits; dividing by T before
# the softmax corrects the model's systematic under-confidence.
TEMPERATURE = 0.5913705321969809

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}

# crop key -> (friendly label, the crop token used inside the model's class names)
# Ordering puts the crops that overlap ANNADATA's own catalogue first.
SUPPORTED_CROPS: tuple[dict[str, str], ...] = (
    {"key": "maize", "label": "Maize (Corn)", "model_crop": "Corn_(maize)"},
    {"key": "tomato", "label": "Tomato", "model_crop": "Tomato"},
    {"key": "potato", "label": "Potato", "model_crop": "Potato"},
    {"key": "pepper_bell", "label": "Bell Pepper", "model_crop": "Pepper,_bell"},
    {"key": "soybean", "label": "Soybean", "model_crop": "Soybean"},
    {"key": "apple", "label": "Apple", "model_crop": "Apple"},
    {"key": "grape", "label": "Grape", "model_crop": "Grape"},
    {"key": "cherry", "label": "Cherry", "model_crop": "Cherry_(including_sour)"},
    {"key": "peach", "label": "Peach", "model_crop": "Peach"},
    {"key": "strawberry", "label": "Strawberry", "model_crop": "Strawberry"},
    {"key": "blueberry", "label": "Blueberry", "model_crop": "Blueberry"},
    {"key": "raspberry", "label": "Raspberry", "model_crop": "Raspberry"},
    {"key": "squash", "label": "Squash", "model_crop": "Squash"},
    {"key": "orange", "label": "Orange", "model_crop": "Orange"},
)

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._\-\u00C0-\u024F ]+")


class ModelUnavailable(RuntimeError):
    """The optional ML dependencies or the model file are not present."""


class CropNotSupported(ValueError):
    """The requested crop is outside the model's documented coverage."""


class InvalidImage(ValueError):
    """The uploaded bytes are not a usable image."""


@dataclass
class PredictResult:
    status: str
    predicted_class: str
    predicted_crop: str
    predicted_crop_label: str
    predicted_disease_label: str
    is_healthy: bool
    confidence: float
    candidates: list[dict[str, Any]]
    image_width: int
    image_height: int
    latency_ms: int
    model_name: str = MODEL_NAME
    model_version: str = MODEL_VERSION


# --- paths ------------------------------------------------------------------


def model_dir() -> Path:
    return Path(settings.DISEASE_MODEL_DIR)


def model_path() -> Path:
    return model_dir() / MODEL_FILENAME


def classes_path() -> Path:
    return model_dir() / CLASSES_FILENAME


def is_available() -> bool:
    return model_path().is_file() and classes_path().is_file()


# --- coverage helpers -------------------------------------------------------


def supported_crop_keys() -> list[str]:
    return [crop["key"] for crop in SUPPORTED_CROPS]


def crop_meta(crop_key: str) -> Optional[dict[str, str]]:
    for crop in SUPPORTED_CROPS:
        if crop["key"] == crop_key:
            return crop
    return None


def supported_crop_labels() -> str:
    return ", ".join(crop["label"] for crop in SUPPORTED_CROPS)


def safe_image_name(name: str) -> str:
    """Keep only the basename and a safe character subset."""
    base = Path(name or "").name
    base = _SAFE_NAME_RE.sub("", base).strip(" .")
    return (base or "leaf-image")[:255]


def _clean(text: str) -> str:
    return " ".join(text.replace("_", " ").split())


def _split_class(class_name: str) -> tuple[str, str]:
    if "___" in class_name:
        crop_token, disease = class_name.split("___", 1)
    else:
        crop_token, disease = class_name, ""
    return crop_token, disease


def _crop_label_for_token(token: str) -> str:
    for crop in SUPPORTED_CROPS:
        if crop["model_crop"] == token:
            return crop["label"]
    return _clean(token)


# --- model / class loading --------------------------------------------------

_classes_cache: Optional[list[str]] = None
_session: Any = None
_session_lock = threading.Lock()


def load_classes() -> list[str]:
    global _classes_cache
    if _classes_cache is None:
        path = classes_path()
        if not path.is_file():
            raise ModelUnavailable(
                "The disease model's class list is missing. Run "
                "`python scripts/download_disease_model.py` in the backend."
            )
        _classes_cache = json.loads(path.read_text("utf-8"))
    return _classes_cache


def load_session():
    """Load (once) and return the ONNX inference session."""
    global _session
    if _session is None:
        with _session_lock:
            if _session is None:
                path = model_path()
                if not path.is_file():
                    raise ModelUnavailable(
                        "The disease model file is not installed. Run "
                        "`python scripts/download_disease_model.py` in the backend."
                    )
                try:
                    import onnxruntime as ort
                except ImportError as exc:  # pragma: no cover - environment dependent
                    raise ModelUnavailable(
                        "The 'onnxruntime' package is required for disease "
                        "identification and is not installed."
                    ) from exc
                options = ort.SessionOptions()
                options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                _session = ort.InferenceSession(
                    str(path),
                    sess_options=options,
                    providers=["CPUExecutionProvider"],
                )
    return _session


def supported_crops() -> list[dict[str, Any]]:
    """The crops the model can assess, each with its detectable conditions."""
    classes = load_classes()
    by_crop: dict[str, list[dict[str, Any]]] = {}
    for name in classes:
        crop_token, disease = _split_class(name)
        disease_label = _clean(disease) or "Unknown"
        by_crop.setdefault(crop_token, []).append(
            {
                "class_name": name,
                "disease_label": disease_label,
                "is_healthy": disease_label.lower() == "healthy",
            }
        )
    return [
        {"key": crop["key"], "label": crop["label"], "diseases": by_crop.get(crop["model_crop"], [])}
        for crop in SUPPORTED_CROPS
    ]


# --- image handling ---------------------------------------------------------


def _decode(data: bytes):
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ModelUnavailable(
            "The 'Pillow' package is required for disease identification and is "
            "not installed."
        ) from exc

    Image.MAX_IMAGE_PIXELS = settings.DISEASE_MAX_IMAGE_PIXELS
    try:
        with Image.open(BytesIO(data)) as img:
            image_format = (img.format or "").upper()
            if image_format not in ALLOWED_IMAGE_FORMATS:
                raise InvalidImage(
                    "Unsupported image format. Upload a JPEG, PNG or WebP leaf photo."
                )
            img.load()
            return img.convert("RGB")
    except InvalidImage:
        raise
    except Image.DecompressionBombError as exc:
        raise InvalidImage("That image is too large to process. Upload a smaller photo.") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImage(
            "That file could not be read as an image. Upload a JPEG, PNG or WebP leaf photo."
        ) from exc


def _to_tensor(image):
    import numpy as np
    from PIL import Image

    width, height = image.size
    if width <= height:
        new_w = RESIZE_SHORT_SIDE
        new_h = max(RESIZE_SHORT_SIDE, round(height * RESIZE_SHORT_SIDE / width))
    else:
        new_h = RESIZE_SHORT_SIDE
        new_w = max(RESIZE_SHORT_SIDE, round(width * RESIZE_SHORT_SIDE / height))
    resized = image.resize((new_w, new_h), Image.BILINEAR)
    left = (new_w - INPUT_SIZE) // 2
    top = (new_h - INPUT_SIZE) // 2
    cropped = resized.crop((left, top, left + INPUT_SIZE, top + INPUT_SIZE))

    array = np.asarray(cropped, dtype=np.float32) / 255.0
    mean = np.array(IMAGENET_MEAN, dtype=np.float32)
    std = np.array(IMAGENET_STD, dtype=np.float32)
    array = (array - mean) / std
    array = np.transpose(array, (2, 0, 1))
    return np.expand_dims(array, 0).astype(np.float32)


def _softmax(logits):
    import numpy as np

    shifted = logits - np.max(logits)
    exp = np.exp(shifted)
    return exp / np.sum(exp)


def predict(image_bytes: bytes, crop_key: str) -> PredictResult:
    """Run the real model on ``image_bytes`` for the selected ``crop_key``."""
    crop = crop_meta(crop_key)
    if crop is None:
        raise CropNotSupported(crop_key)

    started = time.perf_counter()
    image = _decode(image_bytes)
    image_width, image_height = image.size
    tensor = _to_tensor(image)

    session = load_session()
    classes = load_classes()
    input_name = session.get_inputs()[0].name
    logits = session.run(["logits"], {input_name: tensor})[0][0]
    probabilities = _softmax(logits / TEMPERATURE)

    order = probabilities.argsort()[::-1]
    candidates: list[dict[str, Any]] = []
    for index in order[:3]:
        index = int(index)
        crop_token, disease = _split_class(classes[index])
        disease_label = _clean(disease) or "Unknown"
        candidates.append(
            {
                "class_name": classes[index],
                "crop_label": _crop_label_for_token(crop_token),
                "disease_label": disease_label,
                "is_healthy": disease_label.lower() == "healthy",
                "confidence": round(float(probabilities[index]), 6),
            }
        )

    best = candidates[0]
    best_index = int(order[0])
    predicted_class = classes[best_index]
    predicted_crop, _ = _split_class(predicted_class)
    is_healthy = bool(best["is_healthy"])
    confidence = float(best["confidence"])

    if predicted_crop != crop["model_crop"]:
        status = STATUS_CROP_MISMATCH
    elif confidence < settings.DISEASE_CONFIDENCE_THRESHOLD:
        status = STATUS_LOW_CONFIDENCE
    elif is_healthy:
        status = STATUS_HEALTHY
    else:
        status = STATUS_IDENTIFIED

    latency_ms = int((time.perf_counter() - started) * 1000)
    return PredictResult(
        status=status,
        predicted_class=predicted_class,
        predicted_crop=predicted_crop,
        predicted_crop_label=_crop_label_for_token(predicted_crop),
        predicted_disease_label=str(best["disease_label"]),
        is_healthy=is_healthy,
        confidence=confidence,
        candidates=candidates,
        image_width=image_width,
        image_height=image_height,
        latency_ms=latency_ms,
    )


__all__ = [
    "PredictResult",
    "ModelUnavailable",
    "CropNotSupported",
    "InvalidImage",
    "MODEL_NAME",
    "MODEL_VERSION",
    "MODEL_FILENAME",
    "CLASSES_FILENAME",
    "SUPPORTED_CROPS",
    "ASSESSMENT_STATUSES",
    "STATUS_IDENTIFIED",
    "STATUS_HEALTHY",
    "STATUS_LOW_CONFIDENCE",
    "STATUS_CROP_MISMATCH",
    "model_dir",
    "model_path",
    "classes_path",
    "is_available",
    "load_classes",
    "load_session",
    "supported_crops",
    "supported_crop_keys",
    "supported_crop_labels",
    "crop_meta",
    "safe_image_name",
    "predict",
]
