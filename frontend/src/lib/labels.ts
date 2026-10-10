export const WATER_SOURCE_LABELS: Record<string, string> = {
  rain_fed: "Rain-fed",
  borewell: "Borewell",
  open_well: "Open well",
  canal: "Canal",
  multiple: "Multiple sources",
  other: "Other",
  not_sure: "Not sure",
};

export const WATER_SOURCE_OPTIONS = [
  { value: "rain_fed", label: "Rain-fed", description: "Dependent on rainfall" },
  { value: "borewell", label: "Borewell", description: "Borewell / tubewell" },
  { value: "open_well", label: "Open well", description: "Open well" },
  { value: "canal", label: "Canal", description: "Canal irrigation" },
  { value: "multiple", label: "Multiple sources", description: "More than one source" },
  { value: "other", label: "Other", description: "Something else" },
  { value: "not_sure", label: "Not sure", description: "I'm not certain" },
] as const;

export const WATER_AVAILABILITY_LABELS: Record<string, string> = {
  limited: "Limited",
  moderate: "Moderate",
  good: "Good",
  seasonal: "Seasonal",
  not_sure: "Not sure",
};

export const WATER_AVAILABILITY_OPTIONS = [
  { value: "limited", label: "Limited", description: "Water is scarce most of the year" },
  { value: "moderate", label: "Moderate", description: "Enough for the main season" },
  { value: "good", label: "Good", description: "Reliable supply through the year" },
  { value: "seasonal", label: "Seasonal", description: "Plentiful only in some seasons" },
  { value: "not_sure", label: "Not sure", description: "Not sure yet" },
] as const;

export const SOIL_STATUS_LABELS: Record<string, string> = {
  not_provided: "Not provided yet",
  pending: "Pending — can be added later",
  available: "Verified soil report connected",
};

export const AREA_SOURCE_LABELS: Record<string, string> = {
  calculated_boundary: "Approximate (calculated from your boundary)",
  manual: "Manually entered",
  not_provided: "Not provided",
};

export const AREA_UNIT_LABELS: Record<string, string> = {
  acre: "acres",
  hectare: "hectares",
  bigha: "bigha",
  square_metre: "square meters",
};

export function landStructure(place?: {
  locality?: string | null;
  sub_district?: string | null;
  district?: string | null;
  state?: string | null;
  country?: string | null;
}): string {
  if (!place) return "Location confirmed";
  const parts = [place.locality, place.sub_district, place.district, place.state, place.country].filter(
    Boolean
  );
  return parts.length ? parts.join(", ") : "Location confirmed";
}