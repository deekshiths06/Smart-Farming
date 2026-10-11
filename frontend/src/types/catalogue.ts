export interface CatalogueCrop {
  key: string;
  display_name: string;
  category: string;
  category_label: string;
  synonyms: string[];
  model_supported: boolean;
}

export interface CatalogueCategory {
  key: string;
  label: string;
  count: number;
}

export interface CatalogueSearchResponse {
  items: CatalogueCrop[];
  total: number;
  limit: number;
  offset: number;
  catalogue_size: number;
  model_supported_count: number;
  categories: CatalogueCategory[];
}
