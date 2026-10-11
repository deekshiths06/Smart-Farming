import { api } from "./api";
import type { DiseaseAssessment, DiseaseCrop } from "../types/disease";

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

export function diseaseErrorMessage(err: unknown, fallback: string): string {
  return extractDetail(err) ?? fallback;
}

export const diseaseApi = {
  async crops(): Promise<DiseaseCrop[]> {
    const response = await api.get<DiseaseCrop[]>("/api/disease/crops");
    return response.data;
  },

  async assess(crop: string, file: File, symptoms?: string): Promise<DiseaseAssessment> {
    const form = new FormData();
    form.append("crop", crop);
    if (symptoms && symptoms.trim()) form.append("symptoms", symptoms.trim());
    form.append("file", file);
    const response = await api.post<DiseaseAssessment>("/api/disease/assess", form);
    return response.data;
  },

  async history(limit = 50): Promise<DiseaseAssessment[]> {
    const response = await api.get<DiseaseAssessment[]>("/api/disease/assessments", {
      params: { limit },
    });
    return response.data;
  },

  async remove(id: number): Promise<void> {
    await api.delete(`/api/disease/assessments/${id}`);
  },
};
