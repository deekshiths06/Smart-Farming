import type { CropEvaluation, CropStatus, MatchCategory } from "../types/crop";

export const MATCH_CATEGORY_ORDER: MatchCategory[] = [
  "good_match",
  "possible_option",
  "needs_more_information",
  "important_limitations",
];

export const MATCH_CATEGORY_LABELS: Record<MatchCategory, string> = {
  good_match: "Good match",
  possible_option: "Possible option",
  needs_more_information: "Needs more information",
  important_limitations: "Important limitations",
};

export const MATCH_CATEGORY_HINTS: Record<MatchCategory, string> = {
  good_match:
    "Matches the crop's documented requirements on the recorded soil, water, season and this location's forecast, with every scored factor checked.",
  possible_option:
    "Looks promising on what is recorded so far, but at least one documented requirement could not be checked yet.",
  needs_more_information:
    "Not enough recorded information about this field to judge the crop yet — that is missing data, not a bad crop.",
  important_limitations:
    "A recorded requirement does not match this field right now (for example an essential soil or water need, or the current season).",
};

export const MATCH_CATEGORY_TONE: Record<
  MatchCategory,
  "success" | "warning" | "danger" | "neutral"
> = {
  good_match: "success",
  possible_option: "warning",
  needs_more_information: "neutral",
  important_limitations: "danger",
};

/** Derive the match category, falling back for older persisted evaluations. */
export function matchCategoryOf(result: CropEvaluation): MatchCategory {
  if (result.match_category && MATCH_CATEGORY_ORDER.includes(result.match_category)) {
    return result.match_category;
  }
  if (result.status === "needs_information") return "needs_more_information";
  if (result.status === "not_recommended") return "important_limitations";
  return result.preliminary ? "possible_option" : "good_match";
}

/** The seasons a crop documents, from its own evaluation payload. */
export function cropSeasons(result: CropEvaluation): string[] {
  const season = result.factors?.season?.requirement?.allowed_values;
  return Array.isArray(season) ? (season as string[]) : [];
}

export const CROP_CATEGORY_LABELS: Record<string, string> = {
  cereal: "Cereal",
  millet: "Millet",
  pulse: "Pulse",
  oilseed: "Oilseed",
  fibre: "Fibre",
  vegetable: "Vegetable",
};

export const CROP_STATUS_LABELS: Record<CropStatus, string> = {
  suitable: "Potentially suitable",
  needs_information: "Needs more information",
  not_recommended: "Not recommended now",
};

export const CROP_STATUS_TONE: Record<CropStatus, "success" | "warning" | "danger" | "neutral"> = {
  suitable: "success",
  needs_information: "warning",
  not_recommended: "danger",
};

export const SEASON_LABELS: Record<string, string> = {
  kharif: "Kharif (monsoon)",
  rabi: "Rabi (winter)",
  zaid: "Zaid (summer)",
};

export const RISK_KIND_LABELS: Record<string, string> = {
  heavy_rain: "Heavy rain",
  wet_spell: "Wet spell",
  dry_spell: "Dry spell",
  heat: "Heat",
  cold: "Cold",
};

export const RISK_SEVERITY_TONE: Record<string, "danger" | "warning" | "info"> = {
  high: "danger",
  medium: "warning",
};

export const FACTOR_STATUS_INFO: Record<
  string,
  { label: string; tone: "success" | "warning" | "neutral" | "info" }
> = {
  evaluated: { label: "Evaluated", tone: "success" },
  missing_input: { label: "Needs input", tone: "warning" },
  not_required: { label: "Not required", tone: "neutral" },
  context: { label: "Context", tone: "info" },
};

export const WATER_NEED_LABELS: Record<string, string> = {
  low: "Low need",
  medium: "Medium need",
  high: "High need",
};

export const TEXTURE_VALUE_LABELS: Record<string, string> = {
  sand: "Sandy",
  loamy_sand: "Loamy sand",
  sandy_loam: "Sandy loam",
  loam: "Loam",
  silt_loam: "Silt loam",
  silt: "Silty",
  sandy_clay_loam: "Sandy clay loam",
  clay_loam: "Clay loam",
  silty_clay_loam: "Silty clay loam",
  sandy_clay: "Sandy clay",
  silty_clay: "Silty clay",
  clay: "Clayey",
  other: "Other / unknown",
};

export function seasonLabel(season: string | null | undefined): string {
  if (!season) return "—";
  return SEASON_LABELS[season] ?? season;
}

export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined || Number.isNaN(score)) return "—";
  return `${Math.round(score * 100)}%`;
}

export function factorValueLabel(factor: string, value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (factor === "texture") return TEXTURE_VALUE_LABELS[String(value)] ?? String(value);
  if (factor === "water" || factor === "water_availability") {
    const waterLabels: Record<string, string> = {
      limited: "Limited",
      seasonal: "Seasonal",
      moderate: "Moderate",
      good: "Good",
      not_sure: "Not sure",
    };
    return waterLabels[String(value)] ?? String(value);
  }
  if (factor === "season") return seasonLabel(String(value));
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : String(Math.round(value * 100) / 100);
  }
  return String(value);
}

export function requirementText(requirement: {
  min_value?: number | null;
  max_value?: number | null;
  allowed_values?: string[] | null;
} | null | undefined): string {
  if (!requirement) return "—";
  if (requirement.allowed_values && requirement.allowed_values.length > 0) {
    return requirement.allowed_values
      .map((value) => {
        if (value === "kharif" || value === "rabi" || value === "zaid") {
          return SEASON_LABELS[value] ?? value;
        }
        if (value in TEXTURE_VALUE_LABELS) return TEXTURE_VALUE_LABELS[value];
        if (value === "low" || value === "medium" || value === "high") return `${value} need`;
        return value;
      })
      .join(", ");
  }
  const min = requirement.min_value;
  const max = requirement.max_value;
  if (min !== null && min !== undefined && max !== null && max !== undefined) {
    return `${min} – ${max}`;
  }
  if (min !== null && min !== undefined) return `${min}+`;
  if (max !== null && max !== undefined) return `up to ${max}`;
  return "Not documented";
}

export function factorUnit(factor: string): string {
  switch (factor) {
    case "temperature":
      return "°C";
    case "rainfall":
      return "mm";
    case "duration":
      return "days";
    default:
      return "";
  }
}