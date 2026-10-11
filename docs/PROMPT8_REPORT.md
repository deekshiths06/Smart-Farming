# PROMPT 8 REPORT — Dynamic, Location-Aware Crop Discovery & Recommendation Engine

**Project:** Annadata | **Prompt:** P8 | **Date:** 2026-10-11

---

## 1. Verified cause of the limited crop results

There was **no hidden cap in the backend**. The
recommendation engine loops over **every active crop** and returns a result per
crop (verified in `backend/app/decision_engine/recommendation.py:630`,
`evaluate_field`, which queries `Crop.is_active.is_(True)` with no `LIMIT`), and
the API returns the full list (`backend/app/api/crops.py:99`).

The real cause was the **seeded knowledge base itself**: the catalogue shipped
by migration `0004_crop_intelligence.py` contained exactly **12 crops**. With 12
rows in the database the UI could only ever show at most 12 crops no matter how
many fields, locations or soil reports a farmer had.

Two secondary, cosmetic limits were also found and addressed:

- The only literal result-slice in the frontend was
  `frontend/src/pages/CropRecommendations.tsx` (older revision) —
  `qualifying.slice(0, 3)` — which trimmed the "Highly Recommended" highlight to
  three crops. This was legitimate (a highlight, not a result cap) but its copy
  implied "these are the only ones that fit"; it has been removed.
- `CompareRequest.crop_ids` in `backend/app/schemas/crop.py:303` allows at most
  20 ids. This is a deliberate guard on a **user-selected subset** for side-by-side
  comparison, not a discovery limit, and has been left as-is.

**Conclusion:** the backend was already correct and uncapped; the fix was to
expand the catalogue, surface every result with honest reliability labels, and
make location a genuine driver of scores and ranking (section 6).

---

## 2. Files changed and why

### Backend — catalogue & data honesty
| File | Change |
|---|---|
| `backend/app/data/crop_knowledge.py` | Expanded the expandable catalogue from **12 → 29 crops** and from **9 → 14 named sources**. Added 5 new source institutions (NSRI Indore, DRMR Bharatpur, IIOR Hyderabad, CRIJAF, IIVR Varanasi). Every crop and every requirement keeps a named `source`, `source_url` and shared `date_reviewed`; no yield/price/profit/pest claims. |
| `backend/alembic/versions/0007_crop_catalogue_expansion.py` | New migration (new head `0007`). **Additive & idempotent** upserts: campaigns the new crops/requirements by name + factor, leaves existing rows (including admin edits) untouched, and its `downgrade` removes only the 17 added crops. |
| `backend/tests/test_migrations.py` | Updated to head `0007` and to assert the catalogue now exceeds 25 crops with the new staples present. |

### Backend — engine & API
| File | Change |
|---|---|
| `backend/app/decision_engine/constants.py` | `ENGINE_VERSION` bumped to `1.3.0`. Added `MATCH_CATEGORY_*` constants and `classify_match(status, preliminary)` — the **same existing statuses/thresholds**, just re-labelled for the UI; no new scoring rule was invented. |
| `backend/app/decision_engine/recommendation.py` | `evaluate_crop` now returns `match_category`, `match_category_label`, `supporting` (evaluated factors at/above threshold), `conflicting` (essential + season/region failures) and `missing` (labelled gaps). `_reasons`/`_next_steps` reused the same `fail` set. |
| `backend/app/schemas/crop.py` | `CropEvaluationRead` gains `match_category`, `match_category_label`, `supporting`, `conflicting`, `missing` with empty defaults so historically stored evaluations stay readable. |
| `backend/dump_compare.py` | Harness feed — deterministic offline forecast + soil report so `compare_dump.json` exercises the full category range reproducibly. |

### Frontend
| File | Change |
|---|---|
| `frontend/src/pages/CropRecommendations.tsx` | Rewrote the results area: shows the selected **location + coordinates + assessment date**; "Highly Recommended" now shows **all** confirmed good matches (slice removed); below it the catalogue is displayed **grouped by match category** with a per-group count, hint, and a per-group **"Show all"** (display aid, `GROUP_LIMIT = 6`, **not** a cap on the engine). Added client-side **search (name) + category + season filters**. |
| `frontend/src/lib/crops.ts` | `MATCH_CATEGORY_*` labels/hints/tone/order, `matchCategoryOf(result)` (safe fallback for older persisted rows), `cropSeasons(result)`, `CROP_CATEGORY_LABELS`. |
| `frontend/src/types/crop.ts` | `MatchCategory` + new `CropEvaluation` fields. |
| `frontend/src/components/crops/CropResultCard.tsx` | Added a match-category badge alongside the existing status badge. |
| `frontend/repro-page.mjs` | jsdom harness extended for the new discovery UI (25 checks). |

---

## 3. Catalogue: before → after

**Before (12, migration 0004):** rice, maize, wheat, sorghum, pearl_millet,
finger_millet, groundnut, chickpea, pigeonpea, green_gram, cotton, tomato —
cereal 4 · millet 2 · pulse 3 · oilseed 1 · fibre 1 · vegetable 1.

**After (29):** the 12 above **plus** barley, barnyard_millet, kodo_millet,
foxtail_millet, black_gram, lentil, cowpea, mustard, soybean, sunflower, sesame,
jute, potato, onion, chilli, brinjal, okra —
cereal 5 · millet 5 · pulse 6 · oilseed 5 · fibre 2 · vegetable 6.

The `crops` table at head now returns all 29 as active; `evaluate_field`
evaluates **all 29 every time** and the API returns 29 results (asserted by
`test_generation_evaluates_the_whole_catalogue`).

---

## 4. Sources and gaps

14 named sources, all ICAR institutes / state agricultural universities / FAO
(indicative) / TNAU, each fixed to official domains:

**Original 9:** IRRI Rice Knowledge Bank · ICAR-IIMR · ICAR-IIWBR · ICRISAT ·
UAS Bengaluru/AICRP on Small Millets · ICAR-IIPR · ICAR-CICR · TNAU ·
FAO (indicative water/land).

**Added 5:** ICAR-NSRI Indore (soybean) · ICAR-DRMR Bharatpur (mustard) · ICAR-IIOR
Hyderabad (sunflower/sesame) · ICAR-CRIJAF (jute) · ICAR-IIVR Varanasi
(potato/onion/chilli/brinjal/okra).

**Gaps (recorded honestly, never guessed):** bands are *indicative agronomic
ranges* summarised from those sources to the same factor model (pH, texture,
water, season, temperature, rainfall, duration) the engine already scores.
There is **no regional restriction data** encoded (no crop currently declares a
`region` factor — visible as `not_required` in every result), no groundwater
depth, no pest/disease pressure, and no variety-level models. Nothing about the
field's long-term agroclimatology beyond the live forecast. Irrigation-need and
sowing-window fine-tuning remain future data-model work (section 7).

---

## 5. How soil and location influence discovery and ranking

- **Soil** has always been the primary driver: pH and texture are essential
  weighted factors (`ph`, `texture` weight 1.0) and a recorded mismatch flags
  `important_limitations`; an absent test is a reported gap (`missing_input`),
  never a refusal. **No precise pH/NPK is ever inferred from coordinates** — the
  value comes only from a soil report, and "no soil round" crops surface as
  *Possible option* (preliminary), never as a confirmed *Good match*
  (`test_missing_soil_is_preliminary_never_a_confirmed_good_match`).
- **Location** enters through the **live Open-Meteo forecast**, not as an
  arbitrary bonus: temperature and rainfall are scored against each crop's
  documented band (rainfall pro-rated by the crop's own duration over the
  forecast window). Two fields with identical soil/water but different forecasts
  get *different* scores and rankings (`test_two_locations_change_ranking_through_the_forecast`),
  and different soil textures produce different texture scores
  (`test_different_soil_textures_change_the_scores`).
- **Match categories** are derived purely from the existing status + whether any
  requirement went unchecked (`classify_match`), so location/soil changes flow
  through to the group a crop lands in, while the actual category boundaries are
  identical to the engine's longstanding thresholds.

---

## 6. Actual test and build results

| Check | Result |
|---|---|
| Backend full suite (`pytest -m "not network"`) | **118 passed**, 3 deselected (live-weather network tests) |
| `tests/test_crops.py` | **47 passed** (was 38; +9 new Prompt-8 tests: catalogue breadth, whole-catalogue generation, category-class mapping, evidence lists, missing-soil honesty, texture sensitivity, location sensitivity, history preservation with categories, compare payload) |
| Backend migrations | Head `0007_crop_catalogue_expansion`; migration tests pass |
| `npm run build` (`tsc -b && vite build`) | **Passed** (only the pre-existing >500 kB chunk-size warning) |
| `npm run lint` (oxlint) | 17 warnings, **all pre-existing**; none in changed files |
| `node repro-page.mjs` (jsdom) | **25/25** checks, no console errors |
| `node repro-actions.mjs` (jsdom) | **31/31** checks, no console errors |

---

## 7. Limitations that need more agronomic data

- Bands are indicative, source-labelled ranges — close agronomy review per
  variety would tighten them.
- No per-region suitability (crops declare no `region` yet); the factor is
  visible as `not_required` rather than scored.
- No groundwater/depth or soil-moisture retention model beyond texture.
- No pest/disease calendar and no yield/price economics (intentionally).
- Live weather is a short 7-day forecast; long-run agroclimatic norms are not
  encoded.
- Sowing-window fine-tuning per district is not modelled; season scoring stays at
  kharif/rabi/zaid.