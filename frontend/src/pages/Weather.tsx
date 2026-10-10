import { Link } from "react-router-dom";
import {
  CloudSun,
  Droplets,
  MapPin,
  RefreshCw,
  Sprout,
  Wind,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader } from "../components/ui/PageHeader";
import { WeatherSummaryCard } from "../components/ui/WeatherSummaryCard";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { Skeleton } from "../components/ui/Skeleton";
import { useFields } from "../hooks/useFields";
import { useWeather } from "../hooks/useWeather";
import { describeWeatherCode, formatDay, formatTime } from "../lib/weather";
import { landStructure } from "../lib/labels";
import { cn } from "../lib/cn";
import type { DailyWeatherPoint } from "../types/field";

interface ChartPoint {
  time: string;
  temp: number;
}

function DayRow({ point, index }: { point: DailyWeatherPoint; index: number }) {
  const { label, Icon } = describeWeatherCode(point.weather_code);
  const max = point.temperature_2m_max;
  const min = point.temperature_2m_min;
  const rainChance = point.precipitation_probability_max;
  const wind = point.wind_speed_10m_max;

  return (
    <div className="flex items-center gap-3 rounded-card border border-border bg-surface p-3 shadow-card">
      <span className="w-14 shrink-0 text-sm font-semibold text-ink">
        {formatDay(point.time, index)}
      </span>
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
        <Icon className="h-5 w-5" />
      </span>
      <span className="hidden flex-1 truncate text-sm text-ink-soft sm:block">{label}</span>
      <span className="ml-auto flex items-baseline gap-1.5 text-sm">
        {max !== null && max !== undefined && (
          <span className="font-semibold text-ink">{Math.round(max)}°</span>
        )}
        {min !== null && min !== undefined && (
          <span className="text-ink-muted">{Math.round(min)}°</span>
        )}
      </span>
      {rainChance !== null && rainChance !== undefined && (
        <span
          title="Chance of rain"
          className="flex w-12 shrink-0 items-center justify-end gap-1 text-xs font-medium text-sky-700"
        >
          <Droplets className="h-3.5 w-3.5" />
          {rainChance}%
        </span>
      )}
      {wind !== null && wind !== undefined && (
        <span className="hidden w-16 shrink-0 items-center justify-end gap-1 text-xs text-ink-muted md:flex">
          <Wind className="h-3.5 w-3.5" />
          {Math.round(wind)} km/h
        </span>
      )}
    </div>
  );
}

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value?: number | null }>;
  label?: string;
}) {
  if (!active || !payload || payload.length === 0 || payload[0].value === null || payload[0].value === undefined) {
    return null;
  }
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-sm shadow-pop">
      <p className="text-xs text-ink-muted">{label}</p>
      <p className="font-semibold text-ink">{Math.round(payload[0].value)}°C</p>
    </div>
  );
}

export default function Weather() {
  const { fields, loading: fieldsLoading, selectedField } = useFields();
  const { data, loading, error, reload } = useWeather(selectedField?.id);

  if (fieldsLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-20 rounded-panel" />
        <div className="grid gap-6 lg:grid-cols-[1fr_1.15fr]">
          <Skeleton className="h-64 rounded-card" />
          <Skeleton className="h-64 rounded-card" />
        </div>
      </div>
    );
  }

  if (fields.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Weather Intelligence"
          description="Live conditions and forecasts read from the field you select."
          icon={<CloudSun className="h-5 w-5" />}
        />
        <EmptyState
          icon={<CloudSun className="h-8 w-8" />}
          title="Add a field to read its weather"
          description="Weather is read for a real, selected field. Create your first field so ANNADATA can show you live conditions and the coming days."
          action={
            <Link to="/fields/create">
              <Button rightIcon={<Sprout className="h-4 w-4" />}>Create your first field</Button>
            </Link>
          }
        />
      </div>
    );
  }

  const snapshot = data?.weather ?? null;
  const daily = (snapshot?.daily ?? []).slice(0, 7);
  const hourlyRaw = snapshot?.hourly ?? [];
  const hourly = hourlyRaw
    .slice(0, 48)
    .map((point) => ({ time: formatTime(point.time), temp: point.temperature_2m }))
    .filter((point): point is ChartPoint => point.temp !== null && point.temp !== undefined);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Weather Intelligence"
        description="Live conditions and forecasts read from the field you select."
        icon={<CloudSun className="h-5 w-5" />}
        actions={
          <Button variant="outline" onClick={() => void reload()} leftIcon={<RefreshCw className="h-4 w-4" />}>
            Refresh
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-2 text-sm text-ink-muted">
        <span className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-2.5 py-1.5 shadow-card">
          <MapPin className="h-3.5 w-3.5 text-brand-700" />
          {selectedField?.field_name}
        </span>
        <span className="rounded-lg bg-surface-sunken px-2.5 py-1.5">
          {landStructure(selectedField as unknown as { locality?: string | null; sub_district?: string | null; district?: string | null; state?: string | null; country?: string | null })}
        </span>
        <span className="text-xs">Change field from the selector in the top bar.</span>
      </div>

      {error && (
        <ErrorAlert title="Weather could not be loaded" message={error} onRetry={() => void reload()} />
      )}

      {loading && !data ? (
        <div className="grid gap-6 lg:grid-cols-[1fr_1.15fr]">
          <Skeleton className="h-72 rounded-card" />
          <div className="space-y-3">
            {[...Array(5)].map((_, index) => (
              <Skeleton key={index} className="h-16 rounded-card" />
            ))}
          </div>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1fr_1.15fr]">
          <WeatherSummaryCard response={data} loading={loading} onReload={() => void reload()} />

          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold tracking-tight text-ink">7-day outlook</h2>
              {daily.length > 0 && (
                <span className="text-xs text-ink-muted">{daily.length} days</span>
              )}
            </div>
            {daily.length > 0 ? (
              <div className="space-y-2.5">
                {daily.map((point, index) => (
                  <DayRow key={`${point.time}-${index}`} point={point} index={index} />
                ))}
              </div>
            ) : (
              <p className="rounded-card border border-dashed border-border-strong bg-surface p-6 text-center text-sm text-ink-muted">
                The 7-day outlook isn't available for this field right now.
              </p>
            )}
          </section>
        </div>
      )}

      <section className="rounded-panel border border-border bg-surface p-5 shadow-card sm:p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <h2 className="text-lg font-bold tracking-tight text-ink">Hourly temperature</h2>
            <p className="text-xs text-ink-muted">
              {snapshot ? `Next 48 hours at ${snapshot.latitude.toFixed(3)}, ${snapshot.longitude.toFixed(3)}` : "Live series"}
            </p>
          </div>
        </div>
        <div className="mt-4 h-[260px] w-full">
          {hourly.length >= 2 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={hourly} margin={{ top: 8, right: 8, bottom: 0, left: -14 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                <XAxis
                  dataKey="time"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "var(--color-ink-muted)", fontSize: 11 }}
                  minTickGap={32}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "var(--color-ink-muted)", fontSize: 11 }}
                  tickFormatter={(value: number) => `${Math.round(value)}°`}
                  width={44}
                />
                <Tooltip content={<ChartTooltip />} cursor={{ stroke: "var(--color-border-strong)" }} />
                <Line
                  type="monotone"
                  dataKey="temp"
                  stroke="var(--color-brand-600)"
                  strokeWidth={2.5}
                  dot={false}
                  activeDot={{ r: 4, fill: "var(--color-brand-600)", stroke: "var(--color-surface)" }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p
              className={cn(
                "flex h-full items-center justify-center text-sm text-ink-muted"
              )}
            >
              Hourly temperature data isn't available for this field right now.
            </p>
          )}
        </div>
      </section>

      <p className="text-center text-xs leading-relaxed text-ink-muted">
        Weather data comes from live sources at the field's coordinates. Everything shown here is
        real — nothing is invented.
      </p>
    </div>
  );
}