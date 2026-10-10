import { api } from "./api";
import type {
  CompareRead,
  CropDetailRead,
  CropRead,
  RecommendationBatch,
  RecommendationRead,
  RecommendationSummary,
} from "../types/crop";

interface ValidationIssue {
  msg?: string;
  loc?: Array<string | number>;
}

function extractDetail(err: unknown): string | null {
  const verbose = err as {
    response?: { data?: { detail?: string | ValidationIssue[] } };
  };
  const detail = verbose?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((issue) => issue?.msg)
      .filter((msg): msg is string => typeof msg === "string");
    if (messages.length > 0) return messages.join("; ");
  }
  return null;
}

export function cropsErrorMessage(err: unknown, fallback: string): string {
  return extractDetail(err) ?? fallback;
}

export const cropsApi = {
  async listCrops(): Promise<CropRead[]> {
    const response = await api.get<CropRead[]>("/api/crops");
    return response.data;
  },

  async getCrop(cropId: number): Promise<CropDetailRead> {
    const response = await api.get<CropDetailRead>(`/api/crops/${cropId}`);
    return response.data;
  },

  async generate(fieldId: number | string): Promise<RecommendationBatch> {
    const response = await api.post<RecommendationBatch>(
      `/api/fields/${fieldId}/crops/recommendations`,
      {}
    );
    return response.data;
  },

  async compare(
    fieldId: number | string,
    cropIds: number[]
  ): Promise<CompareRead> {
    const response = await api.post<CompareRead>(
      `/api/fields/${fieldId}/crops/compare`,
      { crop_ids: cropIds }
    );
    return response.data;
  },

  async history(fieldId: number | string): Promise<RecommendationSummary[]> {
    const response = await api.get<RecommendationSummary[]>(
      `/api/fields/${fieldId}/crops/recommendations`
    );
    return response.data;
  },

  async recommendation(
    fieldId: number | string,
    recommendationId: number
  ): Promise<RecommendationRead> {
    const response = await api.get<RecommendationRead>(
      `/api/fields/${fieldId}/crops/recommendations/${recommendationId}`
    );
    return response.data;
  },

  async batch(
    fieldId: number | string,
    batchId: string
  ): Promise<RecommendationRead[]> {
    const response = await api.get<RecommendationRead[]>(
      `/api/fields/${fieldId}/crops/recommendations/batches/${batchId}`
    );
    return response.data;
  },
};