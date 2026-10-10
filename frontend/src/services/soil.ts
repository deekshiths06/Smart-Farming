import { api } from "./api";
import type {
  SoilMeasurement,
  SoilMeasurementPayload,
  SoilProfile,
  SoilReport,
} from "../types/soil";

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

export function soilErrorMessage(err: unknown, fallback: string): string {
  return extractDetail(err) ?? fallback;
}

export const soilApi = {
  async getProfile(fieldId: number | string): Promise<SoilProfile> {
    const response = await api.get<SoilProfile>(`/api/fields/${fieldId}/soil`);
    return response.data;
  },

  async createMeasurement(
    fieldId: number | string,
    payload: SoilMeasurementPayload
  ): Promise<SoilMeasurement> {
    const response = await api.post<SoilMeasurement>(
      `/api/fields/${fieldId}/soil/measurements`,
      payload
    );
    return response.data;
  },

  async updateMeasurement(
    fieldId: number | string,
    measurementId: number,
    payload: Partial<SoilMeasurementPayload>
  ): Promise<SoilMeasurement> {
    const response = await api.put<SoilMeasurement>(
      `/api/fields/${fieldId}/soil/measurements/${measurementId}`,
      payload
    );
    return response.data;
  },

  async deleteMeasurement(fieldId: number | string, measurementId: number): Promise<void> {
    await api.delete(`/api/fields/${fieldId}/soil/measurements/${measurementId}`);
  },

  async uploadReport(
    fieldId: number | string,
    file: File,
    meta: { report_date?: string; report_source?: string } = {}
  ): Promise<SoilReport> {
    const form = new FormData();
    form.append("file", file);
    if (meta.report_date) form.append("report_date", meta.report_date);
    if (meta.report_source) form.append("report_source", meta.report_source);
    const response = await api.post<SoilReport>(`/api/fields/${fieldId}/soil/reports`, form);
    return response.data;
  },

  async downloadReport(
    fieldId: number | string,
    report: Pick<SoilReport, "id" | "original_filename">
  ): Promise<void> {
    const response = await api.get(`/api/fields/${fieldId}/soil/reports/${report.id}/download`, {
      responseType: "blob",
    });
    const url = URL.createObjectURL(response.data as Blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = report.original_filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};
