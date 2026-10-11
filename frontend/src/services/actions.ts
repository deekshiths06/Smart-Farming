import { api } from "./api";
import type { ActionPlanRead, ActionRead } from "../types/action";

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

export function actionsErrorMessage(err: unknown, fallback: string): string {
  return extractDetail(err) ?? fallback;
}

export const actionsApi = {
  async plan(fieldId: number | string): Promise<ActionPlanRead> {
    const response = await api.get<ActionPlanRead>(`/api/fields/${fieldId}/actions`);
    return response.data;
  },

  async refresh(fieldId: number | string): Promise<ActionPlanRead> {
    const response = await api.post<ActionPlanRead>(
      `/api/fields/${fieldId}/actions/refresh`,
      {}
    );
    return response.data;
  },

  async setCompleted(
    fieldId: number | string,
    actionId: number,
    completed: boolean
  ): Promise<ActionRead> {
    const response = await api.patch<ActionRead>(
      `/api/fields/${fieldId}/actions/${actionId}`,
      { completed }
    );
    return response.data;
  },
};
