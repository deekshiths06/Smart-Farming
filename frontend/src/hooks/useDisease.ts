import { useCallback, useEffect, useState } from "react";
import { diseaseApi, diseaseErrorMessage } from "../services/disease";
import type { DiseaseAssessment, DiseaseCrop } from "../types/disease";

/**
 * Load the model's supported crops and the signed-in user's screening history,
 * and run new assessments.
 *
 * Nothing here is generated on the client: crops and results come from the
 * backend, which runs the real model. An assessment is only added to the local
 * history after the server has persisted it.
 */
export function useDiseaseIdentification() {
  const [crops, setCrops] = useState<DiseaseCrop[]>([]);
  const [cropsLoading, setCropsLoading] = useState(true);
  const [cropsError, setCropsError] = useState<string | null>(null);

  const [history, setHistory] = useState<DiseaseAssessment[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const [assessing, setAssessing] = useState(false);

  const reloadCrops = useCallback(async () => {
    setCropsLoading(true);
    setCropsError(null);
    try {
      setCrops(await diseaseApi.crops());
    } catch (err) {
      setCropsError(
        diseaseErrorMessage(err, "The list of supported crops could not be loaded.")
      );
    } finally {
      setCropsLoading(false);
    }
  }, []);

  const reloadHistory = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      setHistory(await diseaseApi.history());
    } catch (err) {
      setHistoryError(
        diseaseErrorMessage(err, "Your past assessments could not be loaded.")
      );
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const assess = useCallback(
    async (crop: string, file: File, symptoms?: string): Promise<DiseaseAssessment> => {
      setAssessing(true);
      try {
        const record = await diseaseApi.assess(crop, file, symptoms);
        setHistory((current) => [record, ...current]);
        return record;
      } finally {
        setAssessing(false);
      }
    },
    []
  );

  const remove = useCallback(async (id: number) => {
    await diseaseApi.remove(id);
    setHistory((current) => current.filter((item) => item.id !== id));
  }, []);

  useEffect(() => {
    void reloadCrops();
    void reloadHistory();
  }, [reloadCrops, reloadHistory]);

  return {
    crops,
    cropsLoading,
    cropsError,
    history,
    historyLoading,
    historyError,
    assessing,
    reloadCrops,
    reloadHistory,
    assess,
    remove,
  };
}
