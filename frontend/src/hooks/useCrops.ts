import { useCallback, useEffect, useState } from "react";
import { cropsApi } from "../services/crops";
import type { RecommendationBatch, RecommendationSummary } from "../types/crop";

export function useCrops(fieldId: number | null | undefined) {
  const [batch, setBatch] = useState<RecommendationBatch | null>(null);
  const [history, setHistory] = useState<RecommendationSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reloadHistory = useCallback(async () => {
    if (fieldId === null || fieldId === undefined) return;
    try {
      const list = await cropsApi.history(fieldId);
      setHistory(list);
    } catch {
      // The core results still render; history is secondary.
      setHistory((current) => current);
    }
  }, [fieldId]);

  useEffect(() => {
    if (fieldId === null || fieldId === undefined) {
      setBatch(null);
      setHistory([]);
      setLoading(false);
      return;
    }
    setBatch(null);
    setLoading(true);
    void (async () => {
      try {
        await reloadHistory();
      } finally {
        setLoading(false);
      }
    })();
  }, [fieldId, reloadHistory]);

  const generate = useCallback(async () => {
    if (fieldId === null || fieldId === undefined) return;
    setGenerating(true);
    setError(null);
    try {
      const next = await cropsApi.generate(fieldId);
      setBatch(next);
      await reloadHistory();
      return next;
    } catch (err) {
      setError("The recommendation could not be generated right now. Please try again.");
      throw err;
    } finally {
      setGenerating(false);
    }
  }, [fieldId, reloadHistory]);

  return {
    batch,
    history,
    loading,
    generating,
    error,
    generate,
    reloadHistory,
  };
}