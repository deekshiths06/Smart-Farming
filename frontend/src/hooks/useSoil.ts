import { useCallback, useEffect, useState } from "react";
import { soilApi } from "../services/soil";
import type { SoilMeasurementPayload, SoilProfile } from "../types/soil";

interface SoilState {
  data: SoilProfile | null;
  loading: boolean;
  error: string | null;
}

export function useSoil(fieldId: number | null | undefined) {
  const [state, setState] = useState<SoilState>({ data: null, loading: false, error: null });

  const reload = useCallback(async () => {
    if (fieldId === null || fieldId === undefined) {
      setState({ data: null, loading: false, error: null });
      return;
    }
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const data = await soilApi.getProfile(fieldId);
      setState({ data, loading: false, error: null });
    } catch {
      setState({
        data: null,
        loading: false,
        error: "The soil record could not be loaded right now.",
      });
    }
  }, [fieldId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const createMeasurement = useCallback(
    async (payload: SoilMeasurementPayload) => {
      if (fieldId === null || fieldId === undefined) return;
      await soilApi.createMeasurement(fieldId, payload);
      await reload();
    },
    [fieldId, reload]
  );

  const updateMeasurement = useCallback(
    async (measurementId: number, payload: Partial<SoilMeasurementPayload>) => {
      if (fieldId === null || fieldId === undefined) return;
      await soilApi.updateMeasurement(fieldId, measurementId, payload);
      await reload();
    },
    [fieldId, reload]
  );

  const deleteMeasurement = useCallback(
    async (measurementId: number) => {
      if (fieldId === null || fieldId === undefined) return;
      await soilApi.deleteMeasurement(fieldId, measurementId);
      await reload();
    },
    [fieldId, reload]
  );

  const uploadReport = useCallback(
    async (file: File, meta: { report_date?: string; report_source?: string }) => {
      if (fieldId === null || fieldId === undefined) return;
      await soilApi.uploadReport(fieldId, file, meta);
      await reload();
    },
    [fieldId, reload]
  );

  return {
    ...state,
    reload,
    createMeasurement,
    updateMeasurement,
    deleteMeasurement,
    uploadReport,
  };
}
