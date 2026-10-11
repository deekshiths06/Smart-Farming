export type CropStatus = "suitable" | "not_recommended" | "needs_information";

export type MatchCategory =
  | "good_match"
  | "possible_option"
  | "needs_more_information"
  | "important_limitations";

export type FactorStatus = "evaluated" | "missing_input" | "not_required" | "context";

export interface CropRequirement {
  id: number;
  crop_id: number;
  factor: string;
  factor_label: string;
  min_value: number | null;
  max_value: number | null;
  allowed_values: string[] | null;
  is_essential: boolean;
  explanation: string | null;
  source: string;
  source_url: string | null;
  sequence: number;
  is_active: boolean;
}

export interface CropRead {
  id: number;
  name: string;
  display_name: string;
  category: string;
  description: string | null;
  is_active: boolean;
  source: string;
  source_url: string | null;
  date_reviewed: string | null;
}

export interface CropDetailRead extends CropRead {
  requirements: CropRequirement[];
}

/** Compact requirement band as stored inside a factor evaluation. */
export interface RequirementDict {
  factor: string;
  min_value: number | null;
  max_value: number | null;
  allowed_values: string[] | null;
  is_essential?: boolean;
  explanation: string | null;
  source?: string;
  source_url?: string | null;
}

export interface FactorRead {
  factor: string;
  label: string;
  status: FactorStatus;
  score: number | null;
  weight: number | null;
  input: unknown;
  detail: string;
  requirement?: RequirementDict | null;
  is_essential: boolean;
  source?: string | null;
  source_url?: string | null;
}

export type RiskSeverity = "high" | "medium";

export interface RiskRead {
  kind: string;
  severity: RiskSeverity;
  title: string;
  detail: string;
  basis: string;
  period: string | null;
  value: number | null;
  unit: string | null;
  source: string;
}

export interface CropEvaluation {
  crop_id: number;
  crop_name: string;
  display_name: string;
  category: string;
  description: string | null;
  status: CropStatus;
  status_label: string;
  /** Plain-language grouping derived from the same evidence as `status`.
   * Older persisted batches may not carry it; the client derives a fallback. */
  match_category?: MatchCategory | "";
  match_category_label?: string;
  /** Labels of evaluated factors that met the threshold (why it fits). */
  supporting?: string[];
  /** Labels of factors that genuinely fail for this field (why not). */
  conflicting?: string[];
  /** Labels of documented requirements that could not be checked (what is missing). */
  missing?: string[];
  score: number | null;
  coverage: number;
  /** True when some documented requirement could not be checked (e.g. no soil
   * test yet): the verdict is an evidence-based preliminary estimate, not a
   * refusal. */
  preliminary?: boolean;
  factors: Record<string, FactorRead>;
  context_factors: Record<string, FactorRead>;
  reasons: string[];
  next_steps: string[];
  risks: RiskRead[];
  notes: string[];
  source: string;
  source_url: string | null;
  date_reviewed: string | null;
}

export interface WeatherContext {
  available: boolean;
  source: string | null;
  observed_at: string | null;
  reason: string | null;
  daily: Array<{
    time: string | null;
    precipitation_sum: number | null;
    temperature_2m_max: number | null;
    temperature_2m_min: number | null;
  }>;
}

export interface SoilContext {
  has_measurement: boolean;
  tested_on: string | null;
  is_stale?: boolean;
  is_future?: boolean;
}

export interface ScoringConfigRead {
  weights: Record<string, number>;
  essential_factors: string[];
  suitable_threshold: number;
  min_coverage: number;
  stale_soil_days: number;
}

export interface RecommendationBatch {
  batch_id: string;
  field_id: number;
  field_name: string;
  season: string;
  generated_at: string;
  weather: WeatherContext;
  soil: SoilContext;
  notes: string[];
  config: ScoringConfigRead;
  results: CropEvaluation[];
  disclaimer: string;
}

export interface RecommendationCounts {
  suitable: number;
  needs_information: number;
  not_recommended: number;
}

export interface RecommendationSummary {
  batch_id: string;
  season: string | null;
  engine_version: string;
  created_at: string;
  counts: RecommendationCounts;
  top_crop: string | null;
}

export interface InputSnapshot {
  engine_version: string;
  reference_date: string;
  season: string;
  field: Record<string, unknown>;
  soil: {
    has_measurement: boolean;
    tested_on: string | null;
    age_days: number | null;
    is_stale: boolean;
    is_future: boolean;
    ph: number | null;
    texture: string | null;
    source_kind: string | null;
    measured_parameters: string[];
  };
  weather: WeatherContext;
  scoring: ScoringConfigRead;
}

export interface RecommendationRead {
  id: number;
  batch_id: string;
  field_id: number;
  crop_id: number | null;
  crop_name: string | null;
  display_name: string | null;
  status: CropStatus;
  status_label: string;
  score: number | null;
  coverage: number | null;
  season: string | null;
  engine_version: string;
  created_at: string;
  result: CropEvaluation;
  input_snapshot: InputSnapshot;
}

/** One cell in the per-factor comparison matrix (one crop). */
export interface CompareCellRead {
  crop_id: number;
  status: FactorStatus;
  score: number | null;
  value_label: string;
  requirement_text: string;
  detail: string;
}

/** One scored factor compared across the chosen crops. */
export interface CompareFactorRead {
  factor: string;
  label: string;
  value_label: string;
  compared: boolean;
  explanation: string;
  cells: CompareCellRead[];
}

/** A crop with its position in the comparison ranking. */
export interface CompareRankedRead {
  rank: number;
  crop_id: number;
  display_name: string;
  status: CropStatus;
  status_label: string;
  score: number | null;
  coverage: number;
  /** True when some requirement could not be checked — never a "better" label. */
  preliminary: boolean;
  supporting: string[];
  constraints: string[];
  missing: string[];
}

export interface CompareCollectRead {
  input: string;
  action: string;
}

export interface CompareRead {
  results: CropEvaluation[];
  ranking: CompareRankedRead[];
  factors: CompareFactorRead[];
  differences: string[];
  rank_changers: string[];
  info_to_collect: CompareCollectRead[];
  preliminary_note: string | null;
  context: {
    season: string | null;
    weather: WeatherContext;
    soil: SoilContext;
    config: {
      weights: Record<string, number>;
      essential_factors: string[];
      suitable_threshold: number;
      min_coverage: number;
      stale_soil_days: number;
    };
  };
  disclaimer: string;
}