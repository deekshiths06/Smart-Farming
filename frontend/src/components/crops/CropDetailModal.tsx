import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  CircleHelp,
  CloudSun,
  ExternalLink,
  Info,
  ListChecks,
  ShieldAlert,
  Sprout,
  X,
  XCircle,
} from "lucide-react";
import { Button } from "../ui/Button";
import { StatusBadge } from "../ui/StatusBadge";
import { CropImage } from "./CropImage";
import {
  CROP_STATUS_TONE,
  FACTOR_STATUS_INFO,
  RISK_KIND_LABELS,
  RISK_SEVERITY_TONE,
  factorUnit,
  factorValueLabel,
  formatScore,
  requirementText,
} from "../../lib/crops";
import { cn } from "../../lib/cn";
import type {
  CropEvaluation,
  FactorRead,
  ScoringConfigRead,
  SoilContext,
  WeatherContext,
} from "../../types/crop";

const SCORED_ORDER = ["ph", "texture", "water", "season", "region", "temperature", "rainfall"];
const SEASON_OR_REGION = new Set(["season", "region"]);
// Forecast factors are scored softly: a short spell below a crop's band lowers
// the estimate, so it is shown as a concern rather than hidden.
const WEATHER_FACTORS = new Set(["temperature", "rainfall"]);

interface Categorised {
  supports: FactorRead[];
  mismatches: FactorRead[];
  missing: FactorRead[];
}

/**
 * Split the engine's own factor evaluations into evidence that supports the
 * crop, confirmed mismatches, and inputs it could not check. Mirrors the
 * backend comparison logic and never invents a value: a factor only counts as a
 * mismatch when the engine actually evaluated it below the documented band.
 */
function categorise(crop: CropEvaluation, config: ScoringConfigRead | null): Categorised {
  const supports: FactorRead[] = [];
  const mismatches: FactorRead[] = [];
  const missing: FactorRead[] = [];
  const threshold = config?.suitable_threshold ?? 0.65;
  const essentials = new Set(config?.essential_factors ?? []);

  for (const factor of SCORED_ORDER) {
    const evaluated = crop.factors?.[factor];
    if (!evaluated) continue;
    if (evaluated.status === "missing_input") {
      missing.push(evaluated);
      continue;
    }
    if (evaluated.status !== "evaluated" || evaluated.score === null || evaluated.score === undefined) {
      continue;
    }
    const hardMismatch =
      (SEASON_OR_REGION.has(factor) && evaluated.score === 0) ||
      (essentials.has(factor) && evaluated.score < threshold) ||
      (WEATHER_FACTORS.has(factor) && evaluated.score < threshold);
    if (hardMismatch) mismatches.push(evaluated);
    else if (evaluated.score >= threshold) supports.push(evaluated);
  }
  return { supports, mismatches, missing };
}

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="space-y-2.5">
      <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-muted">
        {icon} {title}
      </h4>
      {children}
    </section>
  );
}

function FactorLine({ factor }: { factor: FactorRead }) {
  const info = FACTOR_STATUS_INFO[factor.status] ?? FACTOR_STATUS_INFO.not_required;
  const missing = factor.status === "missing_input";
  const valueText = missing
    ? "Not recorded yet"
    : `Field value: ${factorValueLabel(factor.factor, factor.input)}`;
  const unit = factor.factor === "temperature" || factor.factor === "rainfall" ? factorUnit(factor.factor) : "";

  return (
    <li className="rounded-card border border-border bg-surface-muted p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-sm font-semibold text-ink">
          {factor.label}
          {factor.is_essential && (
            <span className="rounded-full bg-brand-50 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-brand-700">
              Essential
            </span>
          )}
        </p>
        <div className="flex items-center gap-2">
          <StatusBadge tone={info.tone} dot>
            {info.label}
          </StatusBadge>
          {factor.score !== null && factor.score !== undefined && (
            <span
              className={cn(
                "rounded-lg px-2 py-1 text-sm font-bold",
                factor.score >= 0.65 ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
              )}
            >
              {formatScore(factor.score)}
            </span>
          )}
        </div>
      </div>
      <p className="mt-1 text-xs text-ink-soft">
        {valueText} · Needs: {requirementText(factor.requirement)}
        {unit ? ` ${unit}` : ""}
      </p>
      {factor.detail && <p className="mt-1 text-xs leading-relaxed text-ink-muted">{factor.detail}</p>}
    </li>
  );
}

function Risks({ risks }: { risks: CropEvaluation["risks"] }) {
  if (!risks || risks.length === 0) return null;
  return (
    <Section title="Possible concerns from the forecast" icon={<ShieldAlert className="h-3.5 w-3.5" />}>
      <ul className="space-y-2">
        {risks.map((risk, index) => (
          <li key={index} className="rounded-card border border-border bg-surface-muted p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold text-ink">{RISK_KIND_LABELS[risk.kind] ?? risk.kind}</p>
              <StatusBadge tone={RISK_SEVERITY_TONE[risk.severity] ?? "warning"} dot>
                {risk.severity === "high" ? "High" : "Medium"} severity
              </StatusBadge>
            </div>
            <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">{risk.title}</p>
            <p className="mt-0.5 text-xs leading-relaxed text-ink-muted">{risk.detail}</p>
            <p className="mt-1 text-[11px] text-ink-muted">
              Basis: {risk.basis} · Source: {risk.source}
            </p>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function Bullets({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1.5">
      {items.map((item, index) => (
        <li key={index} className="text-sm leading-relaxed text-ink-soft">
          <span className="mr-1.5 text-ink-muted">•</span>
          {item}
        </li>
      ))}
    </ul>
  );
}

interface CropDetailModalProps {
  open: boolean;
  crop: CropEvaluation | null;
  config: ScoringConfigRead | null;
  soil?: SoilContext | null;
  weather?: WeatherContext | null;
  onClose: () => void;
}

export function CropDetailModal({
  open,
  crop,
  config,
  soil,
  weather,
  onClose,
}: CropDetailModalProps) {
  if (typeof document === "undefined") return null;

  const detail = crop ? categorise(crop, config) : null;

  const hasScore =
    crop !== null && crop.score !== null && crop.score !== undefined && !Number.isNaN(crop.score);

  // Context the engine had to leave out. Listed only when genuinely absent, so
  // a missing soil test can never be shown as a reason a crop is unsuitable.
  const contextMissing: string[] = [];
  if (crop && detail) {
    const missingLabels = new Set(detail.missing.map((factor) => factor.label));
    if (soil && !soil.has_measurement && !missingLabels.has("Soil pH") && !missingLabels.has("Soil texture")) {
      contextMissing.push("No soil test recorded — soil pH and texture were not compared.");
    }
    if (soil?.is_stale || soil?.is_future) {
      contextMissing.push("A soil test exists but is out of date, so it was not used for scoring.");
    }
    if (weather && !weather.available) {
      contextMissing.push(weather.reason ?? "Live weather was not available for this assessment.");
    }
  }

  return createPortal(
    <AnimatePresence>
      {open && crop && detail && (
        <motion.div
          className="fixed inset-0 z-[1100] flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          role="dialog"
          aria-modal="true"
          aria-label={`${crop.display_name} crop details`}
        >
          <div
            className="absolute inset-0 bg-forest-950/45 backdrop-blur-[2px]"
            onClick={onClose}
            aria-hidden="true"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.97, y: 14 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98, y: 10 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="thin-scroll relative flex max-h-[90vh] w-full max-w-2xl flex-col overflow-y-auto rounded-panel border border-border bg-surface shadow-pop"
          >
            <div className="relative">
              <CropImage
                cropName={crop.crop_name}
                displayName={crop.display_name}
                className="h-44 w-full object-cover"
                wrapperClassName="h-44 w-full"
              />
              <button
                type="button"
                onClick={onClose}
                aria-label="Close"
                className="absolute right-3 top-3 rounded-md bg-forest-950/50 p-1.5 text-white transition-colors hover:bg-forest-950/70"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-6 p-5">
              <header className="space-y-2">
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="font-display text-xl font-bold tracking-tight text-ink">
                    {crop.display_name}
                  </h2>
                  <StatusBadge tone={CROP_STATUS_TONE[crop.status] ?? "neutral"} dot>
                    {crop.status_label}
                  </StatusBadge>
                  {hasScore && (
                    <span className="rounded-lg bg-surface-sunken px-2.5 py-1 text-sm font-bold text-ink">
                      {formatScore(crop.score)} suitability
                    </span>
                  )}
                  {crop.preliminary && (
                    <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700 ring-1 ring-inset ring-amber-600/20">
                      Preliminary estimate
                    </span>
                  )}
                </div>
                {crop.description && (
                  <p className="text-sm leading-relaxed text-ink-soft">{crop.description}</p>
                )}
              </header>

              {crop.reasons.length > 0 && (
                <Section title="What the assessment found" icon={<Info className="h-3.5 w-3.5" />}>
                  <Bullets items={crop.reasons} />
                </Section>
              )}

              {detail.supports.length > 0 && (
                <Section
                  title="Why this crop may suit the field"
                  icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                >
                  <ul className="space-y-2">
                    {detail.supports.map((factor) => (
                      <FactorLine key={factor.factor} factor={factor} />
                    ))}
                  </ul>
                </Section>
              )}

              {detail.mismatches.length > 0 && (
                <Section
                  title="Why it may not suit right now"
                  icon={<XCircle className="h-3.5 w-3.5" />}
                >
                  <ul className="space-y-2">
                    {detail.mismatches.map((factor) => (
                      <FactorLine key={factor.factor} factor={factor} />
                    ))}
                  </ul>
                </Section>
              )}

              <Risks risks={crop.risks} />

              <Section title="Still not recorded" icon={<CircleHelp className="h-3.5 w-3.5" />}>
                {detail.missing.length === 0 && contextMissing.length === 0 ? (
                  <p className="text-sm text-ink-soft">
                    Every documented requirement for this crop was checked against your field.
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {detail.missing.map((factor) => (
                      <FactorLine key={factor.factor} factor={factor} />
                    ))}
                    {contextMissing.map((line, index) => (
                      <li
                        key={index}
                        className="flex items-start gap-2 rounded-card border border-border bg-surface-muted p-3 text-sm text-ink-soft"
                      >
                        <CloudSun className="mt-0.5 h-4 w-4 shrink-0 text-ink-muted" />
                        {line}
                      </li>
                    ))}
                  </ul>
                )}
              </Section>

              {crop.next_steps.length > 0 && (
                <Section
                  title="Suggested next step"
                  icon={<ListChecks className="h-3.5 w-3.5" />}
                >
                  <Bullets items={crop.next_steps} />
                </Section>
              )}

              {(crop.notes?.length ?? 0) > 0 && (
                <div className="rounded-card border border-amber-200 bg-amber-50 p-3">
                  <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-amber-700">
                    <AlertTriangle className="h-3.5 w-3.5" /> Notes
                  </h4>
                  <ul className="mt-2 space-y-1.5">
                    {crop.notes.map((note, index) => (
                      <li key={index} className="text-sm leading-relaxed text-amber-800">
                        <span className="mr-1.5 text-amber-600">•</span>
                        {note}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <footer className="flex flex-wrap items-center gap-x-1.5 border-t border-border pt-3 text-[11px] text-ink-muted">
                <span className="inline-flex items-center gap-1">
                  <Sprout className="h-3 w-3" /> Crop knowledge from {crop.source}.
                </span>
                {crop.source_url && (
                  <a
                    href={crop.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-0.5 font-semibold text-brand-700 hover:text-brand-800"
                  >
                    View source <ExternalLink className="h-3 w-3" />
                  </a>
                )}
                {crop.date_reviewed && <span>Reviewed {crop.date_reviewed}.</span>}
              </footer>

              <div className="flex justify-end">
                <Button variant="outline" onClick={onClose}>
                  Close
                </Button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  );
}
