import { useCallback, useEffect, useRef, useState } from "react";
import { actionsApi, actionsErrorMessage } from "../services/actions";
import type { ActionPlanRead } from "../types/action";

/**
 * Load and manage the Smart Farming Action Planner for a field.
 *
 * Actions are generated server-side from the field's recorded data, so loading
 * a plan never invents anything. Toggling a step is optimistic but reverts if
 * the save fails, and completion is only ever changed by the farmer.
 */
export function useActions(fieldId: number | null | undefined) {
  const [plan, setPlan] = useState<ActionPlanRead | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fieldRef = useRef(fieldId);

  const load = useCallback(async () => {
    if (fieldId === null || fieldId === undefined) return;
    setLoading(true);
    setError(null);
    try {
      const next = await actionsApi.plan(fieldId);
      setPlan(next);
    } catch (err) {
      setPlan(null);
      setError(actionsErrorMessage(err, "Your action plan could not be loaded right now."));
    } finally {
      setLoading(false);
    }
  }, [fieldId]);

  const refresh = useCallback(async () => {
    if (fieldId === null || fieldId === undefined) return;
    setRefreshing(true);
    setError(null);
    try {
      const next = await actionsApi.refresh(fieldId);
      setPlan(next);
    } catch (err) {
      setError(actionsErrorMessage(err, "The action plan could not be refreshed right now."));
    } finally {
      setRefreshing(false);
    }
  }, [fieldId]);

  const toggle = useCallback(
    async (actionId: number, completed: boolean) => {
      if (fieldId === null || fieldId === undefined) return;
      const previous = plan;
      setBusyId(actionId);
      setError(null);
      // Optimistic update: reflect the intent immediately.
      setPlan((current) =>
        current
          ? {
              ...current,
              actions: current.actions.map((action) =>
                action.id === actionId
                  ? {
                      ...action,
                      completed,
                      completed_at: completed ? new Date().toISOString() : null,
                    }
                  : action
              ),
            }
          : current
      );
      try {
        const updated = await actionsApi.setCompleted(fieldId, actionId, completed);
        setPlan((current) =>
          current
            ? {
                ...current,
                actions: current.actions.map((action) =>
                  action.id === updated.id ? updated : action
                ),
              }
            : current
        );
      } catch (err) {
        setPlan(previous);
        setError(
          actionsErrorMessage(err, "That change could not be saved. Please try again.")
        );
      } finally {
        setBusyId(null);
      }
    },
    [fieldId, plan]
  );

  useEffect(() => {
    if (fieldRef.current !== fieldId) {
      fieldRef.current = fieldId;
      setPlan(null);
      setError(null);
    }
    void load();
  }, [fieldId, load]);

  return { plan, loading, refreshing, busyId, error, reload: load, refresh, toggle };
}
