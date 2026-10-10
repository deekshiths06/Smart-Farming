import {
  Atom,
  Droplets,
  FlaskConical,
  Layers,
  Leaf,
  Mountain,
  Sprout,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { StatusBadge } from "../ui/StatusBadge";
import { cn } from "../../lib/cn";
import { SOIL_PARAMETER_MAP, SOIL_PARAMETER_METHOD, SOIL_STATUS_META, formatParamValue } from "../../lib/soil";
import type { ParamAssessment, SoilParameterKey } from "../../types/soil";

const ICONS: Record<SoilParameterKey, LucideIcon> = {
  ph: FlaskConical,
  nitrogen: Leaf,
  phosphorus: Sprout,
  potassium: Atom,
  ec: Zap,
  organic_carbon: Layers,
  moisture: Droplets,
  texture: Mountain,
};

function gaugePosition(
  value: number | null | undefined,
  min: number | null,
  max: number | null
): number | null {
  if (
    value === null ||
    value === undefined ||
    min === null ||
    max === null ||
    max <= min
  ) {
    return null;
  }
  const ratio = (value - min) / (max - min);
  return Math.min(100, Math.max(0, Math.round(ratio * 100)));
}

export function SoilParameterCard({ assessment }: { assessment: ParamAssessment }) {
  const meta = SOIL_PARAMETER_MAP[assessment.parameter];
  const status = SOIL_STATUS_META[assessment.status];
  const Icon = ICONS[assessment.parameter];
  const isTexture = assessment.parameter === "texture";
  const method = SOIL_PARAMETER_METHOD[assessment.parameter];
  const labOnly = assessment.requires_lab;

  const label = assessment.label || meta?.label || assessment.parameter;
  const unit = assessment.unit ?? meta?.unit ?? "";

  const hasRange =
    assessment.min_value !== null && assessment.max_value !== null;
  const rangeText = hasRange
    ? `${assessment.min_value}–${assessment.max_value}${unit ? ` ${unit}` : ""}`
    : null;

  const valueText = isTexture
    ? assessment.texture_label ?? "—"
    : meta
      ? formatParamValue(meta, assessment.value)
      : assessment.value === null
        ? "—"
        : String(assessment.value);

  const gauge = gaugePosition(assessment.value, assessment.min_value, assessment.max_value);

  const iconTone =
    assessment.status === "within"
      ? "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-100"
      : assessment.status === "below" || assessment.status === "above"
        ? "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-100"
        : "bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-100";

  const gaugeTone =
    assessment.status === "within"
      ? "bg-emerald-500"
      : assessment.status === "below" || assessment.status === "above"
        ? "bg-amber-400"
        : "bg-brand-400";

  return (
    <div className="group flex flex-col rounded-card border border-border bg-surface p-4 shadow-card transition-shadow hover:shadow-pop">
      <div className="flex items-start gap-3">
        <span className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-lg", iconTone)}>
          <Icon className="h-4.5 w-4.5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-ink">{label}</p>
          <p className="font-display mt-0.5 text-xl font-extrabold tracking-tight text-ink">
            {valueText}
            {!isTexture && assessment.value !== null && unit && (
              <span className="ml-1 text-[11px] font-semibold text-ink-muted">{unit}</span>
            )}
          </p>
        </div>
      </div>

      {hasRange && (
        <div className="mt-3">
          <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-surface-sunken">
            <div
              className={cn("h-full rounded-full transition-[width] duration-300", gaugeTone)}
              style={{ width: `${gauge ?? 0}%` }}
            />
            {gauge !== null && (
              <span
                className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface bg-ink shadow-soft"
                style={{ left: `${gauge}%` }}
                aria-hidden="true"
              />
            )}
          </div>
          <div className="mt-1 flex items-center justify-between text-[11px] text-ink-muted">
            <span className="truncate">
              {assessment.range_label ? `${assessment.range_label} · ` : ""}
              {rangeText}
            </span>
            <StatusBadge tone={status.tone} dot>
              {status.label}
            </StatusBadge>
          </div>
        </div>
      )}

      {!hasRange && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <StatusBadge tone={status.tone} dot>
            {status.label}
          </StatusBadge>
          {rangeText && (
            <span className="text-[11px] text-ink-muted">
              {assessment.range_label ? `${assessment.range_label} · ` : ""}
              {rangeText}
            </span>
          )}
        </div>
      )}

      {method && (
        <p className="mt-2 flex items-center gap-1.5 text-[11px] text-ink-muted">
          <span
            className={cn(
              "rounded-full px-2 py-0.5 font-semibold uppercase tracking-wide",
              labOnly ? "bg-amber-50 text-amber-700" : "bg-surface-sunken text-ink-muted"
            )}
          >
            {labOnly ? "Needs lab test" : method.label}
          </span>
        </p>
      )}

      <p className="mt-3 text-xs leading-relaxed text-ink-muted">{assessment.explanation}</p>

      {(assessment.applied_context || assessment.source) && (
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-border pt-2.5 text-[11px] text-ink-muted">
          {assessment.applied_context && <span>{assessment.applied_context}</span>}
          {assessment.source && (
            <span className="inline-flex items-center gap-1">
              Source:
              {assessment.source_url ? (
                <a
                  href={assessment.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-brand-700 underline-offset-2 hover:underline"
                >
                  {assessment.source}
                </a>
              ) : (
                <span className="font-medium text-ink-soft">{assessment.source}</span>
              )}
            </span>
          )}
        </div>
      )}

      {assessment.source_kind && (
        <p className="mt-2 text-[11px] italic text-ink-muted/90">{assessment.source_kind}</p>
      )}
    </div>
  );
}