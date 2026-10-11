# PROMPT 9 (follow-up) — Searchable Crop Catalogue for Disease Identification

## Summary

The Crop Disease Identification page no longer offers a small fixed list of the
model's crops. The crop selector is now a **searchable combobox backed by
ANNADATA's central crop catalogue (136 crops)**, and the page keeps two things
strictly separate:

- **Catalogue coverage** — every crop a farmer can name, across cereals,
  millets, pulses, oilseeds, vegetables, fruits, spices, plantation/cash crops,
  fibre crops, forage and other crops.
- **AI model coverage** — the 14 crops the installed model was actually trained
  and verified on.

Choosing a crop that is in the catalogue but not in the model shows an honest,
explicit notice and offers no prediction. Nothing is fabricated: no invented
classes, confidence, symptoms or results.

## Catalogue composition

`backend/app/data/crop_catalogue.py` — **136 crops** in 11 categories:

| Category | Count |
| --- | ---: |
| Cereals | 10 |
| Millets | 8 |
| Pulses | 11 |
| Oilseeds | 9 |
| Vegetables | 31 |
| Fruits | 31 |
| Spices & condiments | 14 |
| Plantation & cash crops | 9 |
| Fibre crops | 7 |
| Forage & fodder | 4 |
| Other crops | 2 |
| **Total** | **136** |

The 29 crops already used by Crop Recommendations (`backend/app/data/crop_knowledge.py`)
are reused **verbatim** (same stable `key` slug and `display_name`) so the two
features cannot drift; the catalogue is a strict superset of them. Every crop has
a stable `key`, a `display_name`, a category, and a list of `synonyms`
(common/regional names).

## How search works

`GET /api/catalogue/crops?q=&category=&limit=&offset=` (authenticated, same JWT
as the rest of the app).

- **Case-insensitive, partial matching** over the display name, the stable key
  and all synonyms.
- **Synonyms / regional names** are first-class: `paddy → Rice (paddy)`,
  `HALDI → Turmeric`, `kollu → Horse gram`, `ragi → Finger millet (ragi)`.
- **Ranked relevance**: exact display-name match first, then name prefix, then
  word prefix, then "contains", then key/synonym matches — so the most likely
  crop floats to the top.
- **Paginated**: `limit` 1–500 (default 100), `offset ≥ 0`, with `total` and the
  catalogue size returned. The UI renders at most 100 matches at once and shows a
  "keep typing to narrow it down" hint if more exist, so thousands of crops never
  hit the DOM.
- Each result is annotated with `model_supported: true/false`.

Examples (from the live service):

```
paddy -> [('rice', 'Rice (paddy)', False)]
HALDI -> [('turmeric', 'Turmeric', False)]
tom   -> [('tomato', 'Tomato', True)]
kollu -> [('horse_gram', 'Horse gram', False)]
ragi  -> [('finger_millet', 'Finger millet (ragi)', False)]
zzzzz -> []
```

## Crops the installed model actually supports (14)

Apple, Blueberry, Cherry, Grape, Maize (corn), Orange, Peach, Bell pepper,
Potato, Raspberry, Soybean, Squash, Strawberry, Tomato.

(stable keys: `apple`, `blueberry`, `cherry`, `grape`, `maize`, `orange`,
`peach`, `pepper_bell`, `potato`, `raspberry`, `soybean`, `squash`, `strawberry`,
`tomato`.)

In the combobox these are the only options badged **"Disease AI"**.

## How unsupported crops are handled

Selecting any other catalogue crop (e.g. Rice, Horse gram, Turmeric, Finger
millet) shows exactly:

> This crop is in ANNADATA's crop catalogue, but the current AI disease model has
> not been trained or verified for it. Disease predictions are unavailable for
> this crop yet.

The upload and "Analyse photo" controls are **not** rendered for those crops, so
no prediction can be requested or implied. If the model file is missing
server-side, no crop can be analysed and a separate "unavailable" notice is
shown.

## Files changed

**Backend (new):**
- `backend/app/data/crop_catalogue.py` — the 136-crop catalogue + synonyms.
- `backend/app/services/crop_catalogue.py` — search, ranking, pagination,
  categories, `model_supported` annotation (reads the model's static class
  metadata without loading the model).
- `backend/app/schemas/catalogue.py` — response models.
- `backend/app/api/catalogue.py` — `GET /api/catalogue/crops`.
- `backend/tests/test_catalogue.py` — 13 tests.

**Backend (edited):**
- `backend/app/main.py` — register the catalogue router under `/api/catalogue`.

**Frontend (new):**
- `frontend/src/types/catalogue.ts`
- `frontend/src/services/catalogue.ts`
- `frontend/src/components/ui/Combobox.tsx` — reusable accessible async
  combobox (`role=combobox/listbox/option`, `aria-activedescendant`,
  Arrow Up/Down/Enter/Escape/Home/End, clear button, empty/loading/error states,
  click-outside, capped + scrollable list, mobile-friendly).
- `frontend/repro-disease.mjs` — jsdom harness for the selector.

**Frontend (edited):**
- `frontend/src/pages/CropDisease.tsx` — the native model-only `<select>` is
  replaced by the combobox; catalogue vs model coverage is enforced and the
  exact unsupported notice is shown.

## Test results

- **Backend:** `pytest` — **150 passed** (was 137; **13 new** catalogue tests
  covering auth, catalogue shape/size, category sums, non-truncation, every
  model crop present, case-insensitivity, partial, synonyms, empty results,
  support flags, category filter, pagination without overlap, and ranking).
- **Frontend build:** `npm run build` (`tsc -b && vite build`) — success.
- **Frontend lint:** `npm run lint` (`oxlint`) — no errors (only the same
  informational warnings the rest of the codebase already has).
- **Frontend harness:** `node repro-disease.mjs` — **25/25 checks passed**, no
  console errors. Covers: combobox present / no native `<select>`; list opens on
  focus; catalogue (not just model) results; scroll-capped list; empty-result
  message; partial + case-insensitive match; "Disease AI" badge only on
  supported crops; synonym search (`paddy`, `kollu`, `HALDI`); keyboard
  Arrow/Enter selection; supported crop reveals detected conditions + upload;
  clearing hides the flow; the exact unsupported notice for Rice and Horse gram;
  catalogue API failure surfaced to the user.

## How to run

```powershell
# backend
cd backend; .\venv\Scripts\python.exe -m pytest -q

# frontend
cd frontend; npm run build; npm run lint; node repro-disease.mjs
```

## Honest limitations

- The catalogue is a curated static list (no DB/migration); adding a crop is a
  data change, and it sorts/ranks by the rules above rather than by usage.
- Adding a crop to the catalogue does **not** make the model able to diagnose its
  diseases. Model coverage is fixed at the 14 crops of the installed CropGuard
  ResNet50 model; the UI never blurs the two.
- The combobox renders at most the first 100 matches; more are reachable by
  narrowing the query (a search-as-you-type list, not an infinite virtual list).
