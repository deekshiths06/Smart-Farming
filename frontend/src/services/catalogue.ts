import { api } from "./api";
import type { CatalogueSearchResponse } from "../types/catalogue";

export interface CatalogueSearchParams {
  q?: string;
  category?: string;
  limit?: number;
  offset?: number;
}

/**
 * The crop catalogue is independent of the disease model. It returns every crop
 * a farmer can name, each flagged with `model_supported` so the UI never
 * confuses "in the catalogue" with "the model can analyse it".
 */
export const catalogueApi = {
  async search(params: CatalogueSearchParams = {}): Promise<CatalogueSearchResponse> {
    const response = await api.get<CatalogueSearchResponse>("/api/catalogue/crops", {
      params,
    });
    return response.data;
  },
};
