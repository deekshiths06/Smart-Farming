export type DiseaseStatus = "identified" | "healthy" | "low_confidence" | "crop_mismatch";

export interface DiseaseClass {
  class_name: string;
  disease_label: string;
  is_healthy: boolean;
}

export interface DiseaseCrop {
  key: string;
  label: string;
  diseases: DiseaseClass[];
}

export interface DiseaseCandidate {
  class_name: string;
  crop_label: string;
  disease_label: string;
  is_healthy: boolean;
  confidence: number;
}

export interface DiseaseAssessment {
  id: number;
  user_id: number;
  crop: string;
  crop_label: string;
  image_filename: string;
  image_content_type: string;
  image_size_bytes: number;
  image_width: number | null;
  image_height: number | null;
  symptoms: string | null;
  status: DiseaseStatus;
  predicted_class: string | null;
  predicted_crop: string | null;
  predicted_crop_label: string | null;
  predicted_disease_label: string | null;
  is_healthy: boolean | null;
  confidence: number | null;
  candidates: DiseaseCandidate[] | null;
  model_name: string;
  model_version: string;
  latency_ms: number | null;
  disclaimer: string;
  created_at: string;
}

export const DISEASE_STATUS_LABELS: Record<DiseaseStatus, string> = {
  identified: "Possible condition found",
  healthy: "Leaf looks healthy",
  low_confidence: "Unable to identify reliably",
  crop_mismatch: "Unable to identify reliably",
};

export const DISEASE_STATUS_TONES: Record<
  DiseaseStatus,
  "success" | "warning" | "danger" | "neutral"
> = {
  identified: "danger",
  healthy: "success",
  low_confidence: "warning",
  crop_mismatch: "warning",
};
