/**
 * Explicit, maintainable crop-image mapping.
 *
 * Every supported crop is matched by a stable, normalized crop identifier
 * (derived from the backend `crop_name` slug) — never by fragile substring
 * matching. Each id points at a locally bundled, crop-specific photograph in
 * `public/assets/crops/` (see `CREDITS.md` for sources and licences).
 *
 * There is deliberately no runtime image search: a crop that has no verified
 * photo resolves to `null` and the UI shows a neutral placeholder labelled with
 * the crop name instead of a misleading picture.
 */

/** Canonical crop id → bundled, verified, crop-specific image. */
export const CROP_IMAGE_SRC: Record<string, string> = {
  rice: "/assets/crops/rice.jpg",
  maize: "/assets/crops/maize.jpg",
  wheat: "/assets/crops/wheat.jpg",
  sorghum: "/assets/crops/sorghum.jpg",
  pearl_millet: "/assets/crops/pearl_millet.jpg",
  finger_millet: "/assets/crops/finger_millet.jpg",
  groundnut: "/assets/crops/groundnut.jpg",
  chickpea: "/assets/crops/chickpea.jpg",
  pigeonpea: "/assets/crops/pigeonpea.jpg",
  green_gram: "/assets/crops/green_gram.jpg",
  cotton: "/assets/crops/cotton.jpg",
  tomato: "/assets/crops/tomato.jpg",
  barley: "/assets/crops/barley.jpg",
  barnyard_millet: "/assets/crops/barnyard_millet.jpg",
  kodo_millet: "/assets/crops/kodo_millet.jpg",
  foxtail_millet: "/assets/crops/foxtail_millet.jpg",
  black_gram: "/assets/crops/black_gram.jpg",
  lentil: "/assets/crops/lentil.jpg",
  cowpea: "/assets/crops/cowpea.jpg",
  mustard: "/assets/crops/mustard.jpg",
  soybean: "/assets/crops/soybean.jpg",
  sunflower: "/assets/crops/sunflower.jpg",
  sesame: "/assets/crops/sesame.jpg",
  jute: "/assets/crops/jute.jpg",
  potato: "/assets/crops/potato.jpg",
  onion: "/assets/crops/onion.jpg",
  chilli: "/assets/crops/chilli.jpg",
  brinjal: "/assets/crops/brinjal.jpg",
  okra: "/assets/crops/okra.jpg",
};

/**
 * Common local names / English synonyms → canonical crop id. Handles the
 * aliases called out in the crop knowledge base (Rice/Paddy, Finger millet/Ragi,
 * Green gram/Moong) plus the usual Indian market names.
 */
export const CROP_ALIASES: Record<string, string> = {
  paddy: "rice",
  "rice_paddy": "rice",
  corn: "maize",
  makka: "maize",
  makai: "maize",
  jowar: "sorghum",
  cholam: "sorghum",
  bajra: "pearl_millet",
  bajri: "pearl_millet",
  cumbu: "pearl_millet",
  ragi: "finger_millet",
  "finger-millet": "finger_millet",
  kelvaragu: "finger_millet",
  peanut: "groundnut",
  peanuts: "groundnut",
  "ground_nut": "groundnut",
  moong: "green_gram",
  mung: "green_gram",
  "mung_bean": "green_gram",
  "green-gram": "green_gram",
  "green_gram_bean": "green_gram",
  chana: "chickpea",
  "bengal_gram": "chickpea",
  "garbanzo": "chickpea",
  "garbanzo_bean": "chickpea",
  arhar: "pigeonpea",
  tur: "pigeonpea",
  "red_gram": "pigeonpea",
  "cajanus_cajan": "pigeonpea",
  "cotton_lint": "cotton",
  jau: "barley",
  sanwa: "barnyard_millet",
  "barnyard-grass": "barnyard_millet",
  kodra: "kodo_millet",
  navane: "foxtail_millet",
  urad: "black_gram",
  "urad_dal": "black_gram",
  "urd": "black_gram",
  masoor: "lentil",
  lobia: "cowpea",
  "black_eyed_pea": "cowpea",
  sarson: "mustard",
  "rapeseed": "mustard",
  "mustard-rapeseed": "mustard",
  soya: "soybean",
  "soya_bean": "soybean",
  surajmukhi: "sunflower",
  til: "sesame",
  "sesamum": "sesame",
  aloo: "potato",
  pyaz: "onion",
  mirchi: "chilli",
  "chili": "chilli",
  "chili_pepper": "chilli",
  "chilli_pepper": "chilli",
  eggplant: "brinjal",
  aubergine: "brinjal",
  bhindi: "okra",
  "lady_finger": "okra",
};

/**
 * Reduce any crop label to a stable identifier: lowercase, collapse
 * separators, then resolve known aliases. Uses exact key lookup only (no
 * substring matching), so "rice" can never accidentally match "rice-paddy".
 */
export function normalizeCropId(cropName: string | null | undefined): string | null {
  if (!cropName) return null;
  const normalized = cropName
    .trim()
    .toLowerCase()
    .replace(/[\s.\-/\\]+/g, "_")
    .replace(/[^a-z0-9_]/g, "")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "");
  if (!normalized) return null;
  return CROP_ALIASES[normalized] ?? normalized;
}

/** Verified image URL for a crop, or `null` when none is bundled. */
export function cropImageUrl(cropName: string | null | undefined): string | null {
  const id = normalizeCropId(cropName);
  if (!id) return null;
  return CROP_IMAGE_SRC[id] ?? null;
}
