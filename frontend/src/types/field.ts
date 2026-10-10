export interface FieldBoundary {
  type: "Polygon";
  coordinates: number[][][];
}

export type WaterSource =
  | "rain_fed"
  | "borewell"
  | "open_well"
  | "canal"
  | "multiple"
  | "other"
  | "not_sure";

export type WaterAvailability =
  | "limited"
  | "moderate"
  | "good"
  | "seasonal"
  | "not_sure";

export type SoilStatus = "not_provided" | "pending" | "available";

export type AreaUnit = "acre" | "hectare" | "bigha" | "square_metre";
export type AreaSource = "calculated_boundary" | "manual" | "not_provided";

export interface Field {
  id: number;
  user_id: number;
  field_name: string;
  latitude: number | null;
  longitude: number | null;
  location_accuracy: number | null;
  location_confirmed: boolean;
  address: string | null;
  locality: string | null;
  sub_district: string | null;
  district: string | null;
  state: string | null;
  country: string | null;
  boundary: FieldBoundary | null;
  area: number | null;
  area_unit: AreaUnit;
  area_source: AreaSource;
  water_source: WaterSource | null;
  water_availability: WaterAvailability | null;
  soil_status: SoilStatus;
  created_at: string;
  updated_at: string;
}

export interface Place {
  address?: string | null;
  locality?: string | null;
  sub_district?: string | null;
  district?: string | null;
  state?: string | null;
  country?: string | null;
  source?: string;
}

export interface ReverseGeocodeResponse {
  status: "ok" | "unavailable";
  message?: string | null;
  location?: Place | null;
}

export interface DailyWeatherPoint {
  time?: string | null;
  weather_code?: number | null;
  temperature_2m_max?: number | null;
  temperature_2m_min?: number | null;
  precipitation_sum?: number | null;
  precipitation_probability_max?: number | null;
  wind_speed_10m_max?: number | null;
}

export interface HourlyWeatherPoint {
  time?: string | null;
  temperature_2m?: number | null;
  relative_humidity_2m?: number | null;
  precipitation?: number | null;
  precipitation_probability?: number | null;
  weather_code?: number | null;
  wind_speed_10m?: number | null;
}

export interface WeatherSnapshot {
  source: string;
  latitude: number;
  longitude: number;
  observed_at: string | null;
  temperature_2m: number | null;
  apparent_temperature?: number | null;
  relative_humidity_2m: number | null;
  precipitation: number | null;
  precipitation_probability?: number | null;
  weather_code: number | null;
  wind_speed_10m: number | null;
  daily?: DailyWeatherPoint[];
  hourly?: HourlyWeatherPoint[];
}

export interface WeatherResponse {
  status: "ok" | "unavailable";
  message?: string | null;
  weather?: WeatherSnapshot | null;
}

export interface CreateFieldPayload {
  field_name: string;
  latitude: number;
  longitude: number;
  location_accuracy?: number | null;
  location_confirmed: boolean;
  address?: string | null;
  locality?: string | null;
  sub_district?: string | null;
  district?: string | null;
  state?: string | null;
  country?: string | null;
  boundary?: FieldBoundary | null;
  area?: number | null;
  area_unit?: AreaUnit;
  area_source?: AreaSource;
  water_source?: WaterSource | null;
  water_availability?: WaterAvailability | null;
  soil_status?: SoilStatus;
}

export type UpdateFieldPayload = Partial<CreateFieldPayload>;