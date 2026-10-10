import { api } from "./api";
import type {
  CreateFieldPayload,
  Field,
  Place,
  ReverseGeocodeResponse,
  UpdateFieldPayload,
  WeatherResponse,
} from "../types/field";

export const fieldsApi = {
  async list(): Promise<Field[]> {
    const response = await api.get<Field[]>("/api/fields");
    return response.data;
  },

  async get(id: number | string): Promise<Field> {
    const response = await api.get<Field>(`/api/fields/${id}`);
    return response.data;
  },

  async create(payload: CreateFieldPayload): Promise<Field> {
    const response = await api.post<Field>("/api/fields", payload);
    return response.data;
  },

  async update(id: number | string, payload: UpdateFieldPayload): Promise<Field> {
    const response = await api.put<Field>(`/api/fields/${id}`, payload);
    return response.data;
  },

  async remove(id: number | string): Promise<void> {
    await api.delete(`/api/fields/${id}`);
  },

  async reverseGeocode(latitude: number, longitude: number): Promise<ReverseGeocodeResponse> {
    const response = await api.post<ReverseGeocodeResponse>("/api/location/reverse-geocode", {
      latitude,
      longitude,
    });
    return response.data;
  },

  async weather(id: number | string): Promise<WeatherResponse> {
    const response = await api.get<WeatherResponse>(`/api/fields/${id}/weather`);
    return response.data;
  },
};

export type { Place };