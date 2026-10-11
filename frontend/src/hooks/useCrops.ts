import { useCallback, useEffect, useRef, useState } from "react";
import { cropsApi } from "../services/crops";
import type { RecommendationBatch, RecommendationSummary } from "../types/crop";

/**
 * Load and generate crop recommendations for a field.
 *
 * ``revision`` is an optional signature of the field's own inputs (location,
 * water, etc.). When it changes without the field id changing, any results that
 * are already on screen are cleared and the assessment is regenerated, so the
 * farmer never reads advice that was computed for an older location.
 */
export function useCrops(
  fieldId: number | null | undefined,
  revision?: string | null
) {
  const [batch, setBatch] = useState<RecommendationBatch | null>(null);
  const [history, setHistory] = useState<RecommendationSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fieldRef = useRef(fieldId);
  const revisionRef = useRef(revision);
  const batchRef = useRef<RecommendationBatch | null>(batch);

  useEffect(() => {
    batchRef.current = batch;
  }, [batch]);

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

  useEffect(() => {
    const fieldChanged = fieldRef.current !== fieldId;
    const revisionChanged = !fieldChanged && revisionRef.current !== revision;
    const hadBatch = batchRef.current !== null;
    fieldRef.current = fieldId;
    revisionRef.current = revision;

    if (fieldId === null || fieldId === undefined) {
      setBatch(null);
      setHistory([]);
      setLoading(false);
      return;
    }

    if (fieldChanged || revisionChanged) {
      // Drop results computed for the previous field/inputs so nothing stale shows.
      setBatch(null);
    }

    setLoading(true);
    void (async () => {
      try {
        await reloadHistory();
      } finally {
        setLoading(false);
      }
    })();

    // The field's location or recorded inputs changed: recalculate automatically.
    if (revisionChanged && hadBatch) {
      void generate();
    }
  }, [fieldId, revision, reloadHistory, generate]);

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
