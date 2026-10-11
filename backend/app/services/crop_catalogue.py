"""Crop catalogue search and model-coverage annotation.

Read-only helpers over ``app.data.crop_catalogue``. The catalogue is a static
reference list, so no database or migration is involved: adding a crop is a
one-line edit in the data module and it appears in the selector immediately.

Crucially this module keeps the **catalogue** and the **disease-model coverage**
separate. A crop is ``model_supported`` only when its stable key is one of the
crops the installed image model actually documents - never because it is in the
catalogue.
"""

from __future__ import annotations

import re

from app.data.crop_catalogue import (
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    CROP_CATALOGUE,
)
from app.services import plant_disease_model

_NORMALISE_RE = re.compile(r"[^a-z0-9]+")


def _normalise(value: str) -> str:
    return _NORMALISE_RE.sub(" ", (value or "").lower()).strip()


def model_supported_keys() -> set[str]:
    """The stable keys the installed model documents (static, no model load)."""
    return set(plant_disease_model.supported_crop_keys())


def catalogue_size() -> int:
    return len(CROP_CATALOGUE)


def supported_size() -> int:
    return len(model_supported_keys())


def is_model_supported(key: str) -> bool:
    return key in model_supported_keys()


def _public(entry: dict, supported: set[str]) -> dict:
    return {
        "key": entry["key"],
        "display_name": entry["display_name"],
        "category": entry["category"],
        "category_label": CATEGORY_LABELS.get(entry["category"], entry["category"]),
        "synonyms": list(entry.get("synonyms") or []),
        "model_supported": entry["key"] in supported,
    }


def _match_score(entry: dict, query: str) -> int | None:
    """Rank a catalogue entry against a normalised query.

    Lower is better. Returns ``None`` when the entry does not match. Matching is
    case-insensitive, partial, and covers the display name, the key slug and the
    regional/common synonyms.
    """
    if not query:
        return 0

    display = _normalise(entry["display_name"])
    if display == query:
        return 0
    if display.startswith(query):
        return 1
    if any(word.startswith(query) for word in display.split()):
        return 2
    if query in display:
        return 3

    for term in [_normalise(entry["key"].replace("_", " "))] + [
        _normalise(syn) for syn in entry.get("synonyms") or []
    ]:
        if not term:
            continue
        if term == query:
            return 2
        if term.startswith(query):
            return 3
        if query in term:
            return 4
    return None


def search(
    query: str = "",
    category: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Return ``(page_items, total_matches)`` for a search query."""
    supported = model_supported_keys()
    entries = CROP_CATALOGUE
    if category:
        entries = [entry for entry in entries if entry["category"] == category]

    q = _normalise(query)
    scored: list[tuple[int, dict]] = []
    for entry in entries:
        score = _match_score(entry, q)
        if score is None:
            continue
        scored.append((score, entry))

    if q:
        scored.sort(key=lambda pair: (pair[0], pair[1]["display_name"].lower()))

    page = scored[offset : offset + limit]
    return [_public(entry, supported) for _, entry in page], len(scored)


def get(key: str) -> dict | None:
    for entry in CROP_CATALOGUE:
        if entry["key"] == key:
            return _public(entry, model_supported_keys())
    return None


def categories() -> list[dict]:
    counts: dict[str, int] = {}
    for entry in CROP_CATALOGUE:
        counts[entry["category"]] = counts.get(entry["category"], 0) + 1
    ordered = [c for c in CATEGORY_ORDER if c in counts]
    # Any category not named in the order still shows up, at the end.
    ordered += [c for c in counts if c not in ordered]
    return [
        {"key": category, "label": CATEGORY_LABELS.get(category, category), "count": counts[category]}
        for category in ordered
    ]


__all__ = [
    "search",
    "get",
    "categories",
    "catalogue_size",
    "supported_size",
    "model_supported_keys",
    "is_model_supported",
]
