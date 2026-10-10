import { Droplets, Info, RefreshCw, Wind } from "lucide-react";
import { cn } from "../../lib/cn";
import type { WeatherResponse } from "../../types/field";
import { describeWeatherCode, formatDateTime } from "../../lib/weather";
import { Skeleton } from "./Skeleton";

interface WeatherSummaryCardProps {
  response: WeatherResponse | null;
  loading?: boolean;
  onReload?: () => void;
  className?: string;
}

export function WeatherSummaryCard({ response, loading, onReload, className }: WeatherSummaryCardProps) {
  if (loading) {
    return (
      <div className={cn("rounded-card border border-border bg-surface p-5 shadow-card", className)}>
        <div className="flex items-center gap-3">
          <Skeleton className="h-12 w-12 rounded-xl" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-5 w-24" />
            <Skeleton className="h-3 w-32" />
          </div>
        </div>
        <Skeleton className="mt-4 h-3 w-full" />
        <Skeleton className="mt-2 h-3 w-2/3" />
      </div>
    );
  }

  if (!response || response.status === "unavailable" || !response.weather) {
    return (
      <div
        className={cn(
          "flex items-start gap-3 rounded-card border border-amber-200 bg-amber-50/70 p-5",
          className
        )}
      >
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-700">
          <Info className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-amber-900">Weather is not available right now.</p>
          <p className="mt-0.5 text-xs leading-relaxed text-amber-800">
            {response?.message ??
              "The live weather service did not respond. Your field data is safe."}
          </p>
          {onReload && (
            <button
              type="button"
              onClick={onReload}
              className="mt-2.5 inline-flex items-center gap-1.5 rounded-lg border border-amber-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-amber-800 transition-colors hover:bg-amber-100"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Try again
            </button>
          )}
        </div>
      </div>
    );
  }

  const values = response.weather;
  const { label, Icon } = describeWeatherCode(values.weather_code);

  return (
    <div className={cn("rounded-card border border-border bg-surface p-5 shadow-card", className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50 text-brand-700">
            <Icon className="h-8 w-8" />
          </span>
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-bold tracking-tight text-ink">
                {values.temperature_2m !== null ? `${Math.round(values.temperature_2m)}°C` : "—"}
              </span>
              {values.apparent_temperature !== null &&
                values.apparent_temperature !== undefined && (
                  <span className="text-xs text-ink-muted">
                    feels {Math.round(values.apparent_temperature)}°C
                  </span>
                )}
            </div>
            <p className="mt-0.5 text-sm font-medium text-ink-soft">{label}</p>
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2">
        <Stat
          icon={<Droplets className="h-4 w-4" />}
          label="Humidity"
          value={values.relative_humidity_2m !== null ? `${values.relative_humidity_2m}%` : "—"}
        />
        <Stat
          icon={<Wind className="h-4 w-4" />}
          label="Wind"
          value={values.wind_speed_10m !== null ? `${values.wind_speed_10m} km/h` : "—"}
        />
        <Stat
          icon={<Droplets className="h-4 w-4" />}
          label="Rain"
          value={values.precipitation !== null ? `${values.precipitation} mm` : "—"}
        />
      </div>

      <p className="mt-4 border-t border-border pt-3 text-[11px] leading-relaxed text-ink-muted">
        Source: {values.source} · Point {values.latitude.toFixed(3)}, {values.longitude.toFixed(3)}
        {values.observed_at
          ? ` · observed ${formatDateTime(values.observed_at)}`
          : " · latest available observation"}
      </p>
    </div>
  );
}

function Stat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg bg-surface-sunken px-2.5 py-2">
      <div className="flex items-center gap-1 text-[11px] font-medium text-ink-muted">
        {icon} {label}
      </div>
      <div className="mt-0.5 text-sm font-semibold text-ink-soft">{value}</div>
    </div>
  );
}