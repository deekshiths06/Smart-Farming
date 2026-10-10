import { useCallback, useEffect, useState } from "react";
import { fieldsApi } from "../services/fields";
import type { WeatherResponse } from "../types/field";

interface WeatherState {
  data: WeatherResponse | null;
  loading: boolean;
  error: string | null;
}

export function useWeather(fieldId: number | null | undefined) {
  const [state, setState] = useState<WeatherState>({ data: null, loading: false, error: null });

  const reload = useCallback(async () => {
    if (fieldId === null || fieldId === undefined) {
      setState({ data: null, loading: false, error: null });
      return;
    }
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const data = await fieldsApi.weather(fieldId);
      setState({ data, loading: false, error: null });
    } catch {
      setState({
        data: null,
        loading: false,
        error: "The weather service could not be reached right now.",
      });
    }
  }, [fieldId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { ...state, reload };
}