import {
  Cloud,
  CloudDrizzle,
  CloudFog,
  CloudLightning,
  CloudRain,
  CloudSnow,
  CloudSun,
  Snowflake,
  Sun,
  type LucideIcon,
} from "lucide-react";

export interface WeatherDescriptor {
  label: string;
  Icon: LucideIcon;
}

const FALLBACK: WeatherDescriptor = { label: "Weather", Icon: Cloud };

/**
 * WMO weather interpretation codes used by Open-Meteo.
 * https://open-meteo.com/en/docs
 */
const CODE_MAP: Record<number, WeatherDescriptor> = {
  0: { label: "Clear sky", Icon: Sun },
  1: { label: "Mainly clear", Icon: CloudSun },
  2: { label: "Partly cloudy", Icon: CloudSun },
  3: { label: "Overcast", Icon: Cloud },
  45: { label: "Fog", Icon: CloudFog },
  48: { label: "Depositing rime fog", Icon: CloudFog },
  51: { label: "Light drizzle", Icon: CloudDrizzle },
  53: { label: "Drizzle", Icon: CloudDrizzle },
  55: { label: "Dense drizzle", Icon: CloudDrizzle },
  56: { label: "Light freezing drizzle", Icon: CloudDrizzle },
  57: { label: "Freezing drizzle", Icon: CloudDrizzle },
  61: { label: "Light rain", Icon: CloudRain },
  63: { label: "Rain", Icon: CloudRain },
  65: { label: "Heavy rain", Icon: CloudRain },
  66: { label: "Light freezing rain", Icon: CloudRain },
  67: { label: "Freezing rain", Icon: CloudRain },
  71: { label: "Light snow", Icon: CloudSnow },
  73: { label: "Snow", Icon: CloudSnow },
  75: { label: "Heavy snow", Icon: Snowflake },
  77: { label: "Snow grains", Icon: CloudSnow },
  80: { label: "Light showers", Icon: CloudRain },
  81: { label: "Showers", Icon: CloudRain },
  82: { label: "Violent showers", Icon: CloudRain },
  85: { label: "Snow showers", Icon: CloudSnow },
  86: { label: "Heavy snow showers", Icon: Snowflake },
  95: { label: "Thunderstorm", Icon: CloudLightning },
  96: { label: "Thunderstorm with hail", Icon: CloudLightning },
  99: { label: "Severe thunderstorm", Icon: CloudLightning },
};

export function describeWeatherCode(code: number | null | undefined): WeatherDescriptor {
  if (code === null || code === undefined) return FALLBACK;
  return CODE_MAP[code] ?? FALLBACK;
}

export function formatTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDay(value: string | null | undefined, index: number): string {
  if (index === 0) return "Today";
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, { weekday: "short", day: "numeric" });
}
