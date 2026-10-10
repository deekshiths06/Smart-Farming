import type { CropStatus } from "../types/crop";

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