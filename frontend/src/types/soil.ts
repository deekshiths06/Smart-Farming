export type SoilParameterKey =
  | "ph"
  | "nitrogen"
  | "phosphorus"
  | "potassium"
  | "ec"
  | "organic_carbon"
  | "moisture"
  | "texture";

export type AssessmentStatus =
  | "below"
  | "within"
  | "above"
  | "no_range"
  | "missing"
  | "info";

export type SourceKind = "farmer_entered" | "report_confirmed";

export type SoilTexture =
  | "sand"
  | "loamy_sand"
  | "sandy_loam"
  | "loam"
  | "silt_loam"
  | "silt"
  | "sandy_clay_loam"
  | "clay_loam"
  | "silty_clay_loam"
  | "sandy_clay"
  | "silty_clay"
  | "clay"
  | "other";

export type SoilReportStatus = "uploaded" | "linked";

export interface SoilMeasurement {
  id: number;
  field_id: number;
  user_id: number;
  tested_on: string;
  test_source: string | null;
  source_kind: SourceKind;
  report_id: number | null;
  ph: number | null;
  nitrogen: number | null;
  phosphorus: number | null;
  potassium: number | null;
  ec: number | null;
  organic_carbon: number | null;
  moisture: number | null;
  texture: SoilTexture | null;
  created_at: string;
  updated_at: string;
}

export interface SoilReport {
  id: number;
  field_id: number;
  user_id: number;
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  report_date: string | null;
  report_source: string | null;
  status: SoilReportStatus;
  created_at: string;
  updated_at: string;
}

export interface ParamAssessment {
  parameter: SoilParameterKey;
  label: string;
  unit: string;
  value: number | null;
  texture_label: string | null;
  measured: boolean;
  status: AssessmentStatus;
  range_label: string | null;
  min_value: number | null;
  max_value: number | null;
  explanation: string;
  source: string | null;
  source_url: string | null;
  applied_context: string | null;
  source_kind: string | null;
  requires_lab: boolean;
}

export interface SoilCompleteness {
  measured_count: number;
  total_count: number;
  percent: number;
  missing: SoilParameterKey[];
  measured: SoilParameterKey[];
}

export interface SoilProfile {
  field_id: number;
  field_name: string;
  has_measurements: boolean;
  latest_measurement: SoilMeasurement | null;
  history: SoilMeasurement[];
  reports: SoilReport[];
  completeness: SoilCompleteness;
  last_tested_on: string | null;
  last_tested_source: string | null;
  assessment: Record<SoilParameterKey, ParamAssessment>;
}

export interface SoilMeasurementPayload {
  tested_on: string;
  test_source?: string | null;
  source_kind?: SourceKind;
  report_id?: number | null;
  ph?: number | null;
  nitrogen?: number | null;
  phosphorus?: number | null;
  potassium?: number | null;
  ec?: number | null;
  organic_carbon?: number | null;
  moisture?: number | null;
  texture?: SoilTexture | null;
}
