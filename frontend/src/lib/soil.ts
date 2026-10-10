import type {
  AssessmentStatus,
  SoilParameterKey,
  SoilTexture,
} from "../types/soil";

export interface SoilParameterMeta {
  key: SoilParameterKey;
  label: string;
  shortLabel: string;
  unit: string;
  min: number;
  max: number;
  step: number;
  placeholder: string;
  why: string;
}

// Numeric parameters, in the order they are shown across the app.
export const SOIL_PARAMETERS: SoilParameterMeta[] = [
  {
    key: "ph",
    label: "Soil pH",
    shortLabel: "pH",
    unit: "",
    min: 0,
    max: 14,
    step: 0.1,
    placeholder: "e.g. 6.8",
    why: "pH controls nutrient availability and microbial activity. Most crops grow best near neutral (6.5–7.5).",
  },
  {
    key: "nitrogen",
    label: "Available nitrogen (N)",
    shortLabel: "Nitrogen",
    unit: "kg/ha",
    min: 0,
    max: 2000,
    step: 1,
    placeholder: "e.g. 280",
    why: "Nitrogen drives vegetative growth and is usually the first nutrient to limit yield.",
  },
  {
    key: "phosphorus",
    label: "Available phosphorus (P)",
    shortLabel: "Phosphorus",
    unit: "kg/ha",
    min: 0,
    max: 500,
    step: 1,
    placeholder: "e.g. 22",
    why: "Phosphorus is critical for root growth, flowering and grain fill.",
  },
  {
    key: "potassium",
    label: "Available potassium (K)",
    shortLabel: "Potassium",
    unit: "kg/ha",
    min: 0,
    max: 2000,
    step: 1,
    placeholder: "e.g. 110",
    why: "Potassium supports water balance, stalk strength and disease resistance.",
  },
  {
    key: "ec",
    label: "Electrical conductivity",
    shortLabel: "EC",
    unit: "dS/m",
    min: 0,
    max: 40,
    step: 0.01,
    placeholder: "e.g. 0.8",
    why: "EC measures soluble salts. High salinity restricts water uptake and hurts yield.",
  },
  {
    key: "organic_carbon",
    label: "Organic carbon",
    shortLabel: "Organic carbon",
    unit: "%",
    min: 0,
    max: 15,
    step: 0.01,
    placeholder: "e.g. 0.55",
    why: "Organic carbon is a proxy for soil organic matter and general soil health.",
  },
  {
    key: "moisture",
    label: "Soil moisture",
    shortLabel: "Moisture",
    unit: "%",
    min: 0,
    max: 100,
    step: 0.1,
    placeholder: "e.g. 18",
    why: "Moisture at sampling helps interpret other values. Only meaningful when measured.",
  },
];

// Texture is a descriptive (non-numeric) parameter. It is not part of the
// numeric SOIL_PARAMETERS list above (it has no min/max/step input), but it
// still needs display metadata because the assessment grid renders a card for
// it. Keeping it out of SOIL_PARAMETERS preserves the numeric-only form fields.
export const TEXTURE_META: SoilParameterMeta = {
  key: "texture",
  label: "Soil texture",
  shortLabel: "Texture",
  unit: "",
  min: 0,
  max: 0,
  step: 0,
  placeholder: "Select texture",
  why: "Texture governs drainage, water holding and nutrient retention, and changes which reference ranges apply.",
};

export const SOIL_PARAMETER_MAP: Record<SoilParameterKey, SoilParameterMeta> = {
  ...Object.fromEntries(SOIL_PARAMETERS.map((meta) => [meta.key, meta])),
  [TEXTURE_META.key]: TEXTURE_META,
} as Record<SoilParameterKey, SoilParameterMeta>;

// Every parameter key (including the descriptive texture) with its display label
// and the plain-language reason it matters. Used by cards and the missing list.
export const SOIL_PARAMETER_LABELS: Record<SoilParameterKey, string> = {
  ph: "Soil pH",
  nitrogen: "Available nitrogen (N)",
  phosphorus: "Available phosphorus (P)",
  potassium: "Available potassium (K)",
  ec: "Electrical conductivity",
  organic_carbon: "Organic carbon",
  moisture: "Soil moisture",
  texture: "Soil texture",
};

export const SOIL_PARAMETER_WHY: Record<SoilParameterKey, string> = {
  ph: "pH controls nutrient availability and microbial activity. Most crops grow best near neutral (6.5–7.5); very acid or alkaline soils lock up nutrients.",
  nitrogen:
    "Nitrogen drives vegetative growth and is usually the first nutrient to limit yield. Low available N means the crop may respond to N fertiliser.",
  phosphorus:
    "Phosphorus is critical for root growth, flowering and grain fill. Many Indian soils are low in available P.",
  potassium:
    "Potassium supports water balance, stalk strength and disease resistance. Deficiency is common in light-textured soils.",
  ec: "EC measures soluble salts. High salinity restricts water uptake and hurts germination and yield.",
  organic_carbon:
    "Organic carbon is a proxy for soil organic matter and general soil health: structure, water holding and nutrient cycling.",
  moisture:
    "Moisture at sampling helps interpret other values (e.g. EC drifts with moisture). Only meaningful when actually measured.",
  texture:
    "Texture governs drainage, water holding and nutrient retention, and changes which reference ranges apply.",
};

// How a farmer obtains each value - used to clearly tell apart measurements
// that require a laboratory soil test from ones that can be taken in the field.
export const SOIL_PARAMETER_METHOD: Record<SoilParameterKey, { tone: "lab" | "field"; label: string }> = {
  ph: { tone: "field", label: "Field test" },
  nitrogen: { tone: "lab", label: "Lab test" },
  phosphorus: { tone: "lab", label: "Lab test" },
  potassium: { tone: "lab", label: "Lab test" },
  ec: { tone: "lab", label: "Lab test" },
  organic_carbon: { tone: "lab", label: "Lab test" },
  moisture: { tone: "field", label: "Field test" },
  texture: { tone: "field", label: "Feel test" },
};

export const SOIL_PARAMETER_METHOD_NOTE: Record<SoilParameterKey, string> = {
  ph: "Measured with a pH meter or test kit in the field",
  nitrogen: "From a laboratory soil test (e.g. Soil Health Card)",
  phosphorus: "From a laboratory soil test (e.g. Soil Health Card)",
  potassium: "From a laboratory soil test (e.g. Soil Health Card)",
  ec: "From a laboratory soil test (e.g. Soil Health Card)",
  organic_carbon: "From a laboratory soil test (e.g. Soil Health Card)",
  moisture: "Field measurement (e.g. a soil moisture meter)",
  texture: "Read by feel using the soil texture triangle",
};

export const TEXTURE_OPTIONS: Array<{ value: SoilTexture; label: string }> = [
  { value: "sand", label: "Sandy" },
  { value: "loamy_sand", label: "Loamy sand" },
  { value: "sandy_loam", label: "Sandy loam" },
  { value: "loam", label: "Loam" },
  { value: "silt_loam", label: "Silt loam" },
  { value: "silt", label: "Silty" },
  { value: "sandy_clay_loam", label: "Sandy clay loam" },
  { value: "clay_loam", label: "Clay loam" },
  { value: "silty_clay_loam", label: "Silty clay loam" },
  { value: "sandy_clay", label: "Sandy clay" },
  { value: "silty_clay", label: "Silty clay" },
  { value: "clay", label: "Clayey" },
  { value: "other", label: "Other / unknown" },
];

export const SOIL_STATUS_META: Record<
  AssessmentStatus,
  { label: string; tone: "success" | "warning" | "info" | "neutral" | "danger"; description: string }
> = {
  within: {
    label: "Within range",
    tone: "success",
    description: "Inside the documented reference band for this field.",
  },
  below: {
    label: "Below range",
    tone: "warning",
    description: "Below the ideal reference band — a signal to investigate.",
  },
  above: {
    label: "Above range",
    tone: "warning",
    description: "Above the ideal reference band — a signal to investigate.",
  },
  no_range: {
    label: "No range yet",
    tone: "neutral",
    description: "Recorded, but no verified reference range applies yet.",
  },
  missing: {
    label: "Not recorded",
    tone: "neutral",
    description: "Optional measurement not entered yet.",
  },
  info: {
    label: "Information",
    tone: "info",
    description: "Descriptive guidance, not a range comparison.",
  },
};

export function formatParamValue(meta: SoilParameterMeta, value: number | null): string {
  if (value === null || value === undefined) return "—";
  const decimals = meta.step < 0.1 ? 2 : meta.step < 1 ? 1 : 0;
  return `${value.toFixed(decimals)}${meta.unit ? ` ${meta.unit}` : ""}`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatSoilDate(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}
