import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { History, Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "../ui/Button";
import { cn } from "../../lib/cn";
import {
  SOIL_PARAMETERS,
  SOIL_PARAMETER_MAP,
  TEXTURE_OPTIONS,
  formatSoilDate,
} from "../../lib/soil";
import type { SoilMeasurement, SoilParameterKey } from "../../types/soil";

interface SoilHistoryPanelProps {
  history: SoilMeasurement[];
  onAdd: () => void;
  onEdit: (measurement: SoilMeasurement) => void;
  onDelete: (measurement: SoilMeasurement) => void;
}

const TEXTURE_LABELS: Record<string, string> = Object.fromEntries(
  TEXTURE_OPTIONS.map((option) => [option.value, option.label])
);

export function SoilHistoryPanel({ history, onAdd, onEdit, onDelete }: SoilHistoryPanelProps) {
  const [chartParam, setChartParam] = useState<SoilParameterKey>("ph");

  const meta = SOIL_PARAMETER_MAP[chartParam];

  const chartData = useMemo(() => {
    return [...history]
      .filter((item) => item[chartParam] !== null && item[chartParam] !== undefined)
      .sort((a, b) => a.tested_on.localeCompare(b.tested_on))
      .map((item) => ({
        date: formatSoilDate(item.tested_on),
        value: item[chartParam] as number,
      }));
  }, [history, chartParam]);

  const hasChartableParam = SOIL_PARAMETERS.some((option) =>
    history.some((item) => item[option.key] !== null && item[option.key] !== undefined)
  );

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
            <History className="h-4.5 w-4.5" />
          </span>
          <div>
            <h2 className="text-lg font-bold tracking-tight text-ink">Soil test history</h2>
            <p className="text-xs text-ink-muted">
              {history.length} {history.length === 1 ? "test event" : "test events"} on record
            </p>
          </div>
        </div>
        <Button size="sm" variant="outline" leftIcon={<Plus className="h-4 w-4" />} onClick={onAdd}>
          Add test
        </Button>
      </div>

      {history.length === 0 ? (
        <p className="rounded-card border border-dashed border-border-strong bg-surface p-6 text-center text-sm text-ink-muted">
          No soil tests recorded yet. Add your first measurement above.
        </p>
      ) : (
        <>
          {hasChartableParam && chartData.length >= 2 && (
            <div className="rounded-panel border border-border bg-surface p-5 shadow-card">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-ink">
                    {meta.shortLabel} over time
                  </h3>
                  <p className="text-xs text-ink-muted">
                    {chartData.length} recorded readings
                    {meta.unit ? ` · ${meta.unit}` : ""}
                  </p>
                </div>
                <select
                  value={chartParam}
                  onChange={(event) => setChartParam(event.target.value as SoilParameterKey)}
                  className="h-9 rounded-lg border border-border-strong bg-surface px-3 text-sm text-ink shadow-soft focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/20"
                >
                  {SOIL_PARAMETERS.filter((option) =>
                    history.some(
                      (item) => item[option.key] !== null && item[option.key] !== undefined
                    )
                  ).map((option) => (
                    <option key={option.key} value={option.key}>
                      {option.shortLabel}
                    </option>
                  ))}
                </select>
              </div>
              <div className="mt-4 h-[220px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -14 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                    <XAxis
                      dataKey="date"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fill: "var(--color-ink-muted)", fontSize: 11 }}
                      minTickGap={24}
                    />
                    <YAxis
                      tickLine={false}
                      axisLine={false}
                      tick={{ fill: "var(--color-ink-muted)", fontSize: 11 }}
                      width={48}
                    />
                    <Tooltip
                      contentStyle={{
                        borderRadius: 10,
                        border: "1px solid var(--color-border)",
                        fontSize: 12,
                      }}
                      cursor={{ stroke: "var(--color-border-strong)" }}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="var(--color-brand-600)"
                      strokeWidth={2.5}
                      dot={{ r: 3, fill: "var(--color-brand-600)" }}
                      activeDot={{ r: 5, fill: "var(--color-brand-600)", stroke: "var(--color-surface)" }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          <div className="overflow-hidden rounded-panel border border-border bg-surface shadow-card">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] border-collapse text-sm">
                <thead>
                  <tr className="border-b border-border bg-surface-muted text-left text-xs font-semibold uppercase tracking-wide text-ink-muted">
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Source</th>
                    {SOIL_PARAMETERS.map((option) => (
                      <th key={option.key} className="px-3 py-3 text-right">
                        {option.shortLabel}
                      </th>
                    ))}
                    <th className="px-3 py-3">Texture</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((item) => (
                    <tr key={item.id} className="border-b border-border last:border-0 hover:bg-surface-muted">
                      <td className="whitespace-nowrap px-4 py-3 font-medium text-ink">
                        {formatSoilDate(item.tested_on)}
                      </td>
                      <td className="px-4 py-3 text-ink-soft">
                        <span className="block max-w-[160px] truncate">
                          {item.test_source ?? "—"}
                        </span>
                        {item.source_kind === "report_confirmed" && (
                          <span className="text-[11px] text-brand-700">From report</span>
                        )}
                      </td>
                      {SOIL_PARAMETERS.map((option) => (
                        <td
                          key={option.key}
                          className={cn(
                            "px-3 py-3 text-right tabular-nums",
                            item[option.key] === null || item[option.key] === undefined
                              ? "text-ink-muted/60"
                              : "text-ink"
                          )}
                        >
                          {item[option.key] === null || item[option.key] === undefined
                            ? "—"
                            : String(item[option.key])}
                        </td>
                      ))}
                      <td className="whitespace-nowrap px-3 py-3 text-ink-soft">
                        {item.texture ? (TEXTURE_LABELS[item.texture] ?? item.texture) : "—"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            type="button"
                            onClick={() => onEdit(item)}
                            aria-label="Edit measurement"
                            className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-surface-sunken hover:text-ink"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => onDelete(item)}
                            aria-label="Delete measurement"
                            className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-red-50 hover:text-red-600"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <p className="text-xs text-ink-muted">
            Values are shown in their canonical units — pH unitless, N/P/K in kg/ha, EC in dS/m,
            organic carbon and moisture in %. Missing readings stay blank; ANNADATA never fills
            them in.
          </p>
        </>
      )}
    </section>
  );
}
