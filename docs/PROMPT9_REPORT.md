# PROMPT 9 REPORT — AI Crop Disease Identification

**Project:** Annadata | **Prompt:** P9 | **Date:** 2026-10-11

---

## 1. What was built

An authenticated **Crop Disease Identification** feature: a farmer picks the crop
they photographed, uploads (or captures) a single-leaf photo, optionally adds
notes, and the backend runs a **real trained image-classification model** on the
photo and returns a preliminary screening. Results are stored per user as a
history the farmer can review and delete.

It is a **screening aid, not a diagnosis**. The feature never fabricates a
prediction, never asserts a disease when inference did not run or was
inconclusive, and gives **no chemical / pesticide advice**.

---

## 2. The model (real, not simulated)

### Choice

| Candidate | Verdict |
|---|---|
| **CropGuard ResNet50** (HuggingFace `XiElonMAsk/cropguard-models`, mirror of `AbhiCommits/cropguard-models`) | **Chosen.** ResNet50 fine-tuned on PlantVillage; **38 classes across 14 crops**; held-out accuracy **0.9911** / macro-F1 **0.9865** (leaf-grouped split). CC-BY-SA-4.0. |
| `imaflower/plantvillage-mobilenetv3` (~6.3 MB) | Rejected — only **15 classes** (pepper/potato/tomato), no maize. Too narrow for Annadata's catalogue. |

The served artifact is `cropguard.onnx` (fp32, ~92 MB).

### Verified interface

Inspected directly with `onnxruntime`:

- Input: `input`, shape `[batch, 3, 224, 224]`, float32.
- Output: `logits`, shape `[batch, 38]`, float32 (**raw logits**, softmax applied after scaling).
- One CPU inference ≈ 458 ms first call.

### Preprocessing

Resize the short side to 256 → center-crop 224 → scale to `[0,1]` → ImageNet
mean/std normalisation → NCHW. Matches the model card.

### Calibration

Raw softmax on this model is under-confident, so logits are divided by a
temperature **T = 0.5913705321969809** (from the model's calibration data)
before softmax. The served model and calibration constant are documented in
`backend/README.md`.

### Coverage (honest limits)

14 crops, 38 conditions: apple, blueberry, cherry, corn (maize), grape, orange,
peach, pepper (bell), potato, raspberry, soybean, squash, strawberry, tomato.
Overlap with Annadata's crop catalogue = **maize, tomato, potato, soybean**
(soybean only has a `healthy` class). Crop tokens are extracted from the class
names and exposed via the API, so the UI only ever offers crops the model was
actually trained on.

---

## 3. Files changed and why

### Backend

| File | Change |
|---|---|
| `backend/app/services/plant_disease_model.py` | **New.** Lazy, thread-safe ONNX session load; class list load; preprocessing; temperature-scaled softmax; coverage helpers; `predict()`; status logic. Constants: `MODEL_NAME`, `MODEL_VERSION`, `TEMPERATURE`, `SUPPORTED_CROPS`, and statuses `identified` / `healthy` / `low_confidence` / `crop_mismatch`. Exceptions `ModelUnavailable`, `CropNotSupported`, `InvalidImage`. |
| `backend/app/api/disease.py` | **New** router (`prefix="/api/disease"`): `GET /crops`, `POST /assess` (multipart `file` + `crop` + optional `symptoms`), `GET /assessments`, `GET /assessments/{id}`, `DELETE /assessments/{id}`. Ownership enforced via a `_owned_assessment` 404 helper. Carries the no-chemical `DISCLAIMER`. Unsupported crop / bad image → 422, model missing → 503. |
| `backend/app/models/disease.py` | **New** `DiseaseAssessment` table. Stores crop, **image metadata only — never the bytes** (filename, content-type, size, dimensions), symptoms, status, predicted class/labels, confidence, candidate list (JSON), model name/version, latency, disclaimer, `created_at`. CheckConstraints on status/confidence/size; index on `(user_id, created_at)`. |
| `backend/app/schemas/disease.py` | **New** `DiseaseClassRead`, `DiseaseCropRead`, `DiseaseAssessmentRead`. |
| `backend/app/core/config.py` | Added `DISEASE_MODEL_DIR`, `DISEASE_IMAGE_MAX_SIZE_MB` (5), `DISEASE_IMAGE_MAX_SIZE_BYTES`, `DISEASE_CONFIDENCE_THRESHOLD` (0.60), `DISEASE_MAX_IMAGE_PIXELS` (50M, decompression-bomb guard). |
| `backend/app/main.py` | Registered the disease router under `/api/disease`. |
| `backend/app/models/__init__.py`, `backend/app/models/user.py`, `backend/alembic/env.py` | Wiring: model import, `disease_assessments` relationship, alembic model discovery. |
| `backend/alembic/versions/0008_disease_identification.py` | **New** migration (new head, revises `0007`): creates `disease_assessments` with checks + indexes; reversible `downgrade()`. |
| `backend/requirements.txt` | Added `onnxruntime==1.31.0`, `pillow==12.3.0`; bumped `numpy` to `2.5.4` (cp314 wheels). |
| `backend/.env.example` | Documented the new `DISEASE_*` settings. |
| `backend/scripts/download_disease_model.py` | **New.** Downloads `classes.json` + `cropguard.onnx` from HuggingFace with a size sanity check. |
| `.gitignore` | Ignore `backend/models/plant_disease/*.onnx` (weights not committed). |
| `backend/README.md` | Model setup + attribution section. |

### Frontend

| File | Change |
|---|---|
| `frontend/src/types/disease.ts` | **New** types + status labels/tones. |
| `frontend/src/services/disease.ts` | **New** API client (`crops`, `assess`, `history`, `remove`) reusing the shared axios instance and error-extraction pattern. |
| `frontend/src/hooks/useDisease.ts` | **New** hook: loads supported crops + history, runs assessments, deletes. |
| `frontend/src/pages/CropDisease.tsx` | **New** page: crop select, camera/gallery upload with preview, optional notes, analyse action, result panel (status badge, confidence, closest matches, advisory), "how it works", and history with per-row delete. Honest limitations banner at the top. |
| `frontend/src/App.tsx` | Added `/disease` route. |
| `frontend/src/layouts/DashboardLayout.tsx` | Added "Crop Disease" nav entry (Microscope icon) + section title. |

---

## 4. Privacy & safety

- **Images are never persisted.** Bytes are read in memory, validated, and
  discarded; only metadata is stored. The UI states this explicitly.
- **Upload validation:** content type restricted to JPEG/PNG/WebP, 5 MB cap
  (enforced by reading `max+1` bytes), and a max-pixel guard against
  decompression bombs. Unsafe filenames are sanitised.
- **Per-user authorization:** listing filters by `user_id`; detail/delete go
  through `_owned_assessment` and return 404 for someone else's record.
- **No run → no claim.** If the model is absent the endpoint returns 503 and the
  UI shows "unavailable". If confidence is below threshold it returns
  `low_confidence` ("Unable to identify reliably"), and if the photo looks like a
  different crop it returns `crop_mismatch` — both advise retaking the photo /
  consulting an expert rather than inventing a disease.
- **No chemical advice.** The response and the UI carry only a generic
  disclaimer advising confirmation with a local agricultural extension officer.

---

## 5. Verification

- **Backend suite: 137 passed** (`pytest` from `backend/`), including 16 new
  disease tests: auth required, crop coverage, unsupported-crop/bad-image/empty/
  oversize → 422, model-missing → 503, all four statuses persisted, image bytes
  never stored, filename sanitising, ownership isolation (list empty; detail &
  delete 404 for an intruder), and delete-own → 204.
- **`test_real_model_inference` passes (not skipped)** — genuine end-to-end
  inference through the API with the installed `cropguard.onnx`.
- **Migrations** updated to head `0008`; fresh-upgrade and idempotency tests pass.
- **Frontend:** `npm run build` (tsc + vite) succeeds; `npm run lint` reports
  only pre-existing-style warnings (no errors).

---

## 6. Reproducing the setup

```powershell
# from backend/
pip install -r requirements.txt
python scripts/download_disease_model.py   # fetches classes.json + cropguard.onnx
alembic upgrade head                        # creates disease_assessments
```

Then open the app, go to **Crop Disease**, choose a crop, and upload a leaf
photo.

**Attribution:** CropGuard ResNet50 — CC-BY-SA-4.0 (see `backend/README.md`).
