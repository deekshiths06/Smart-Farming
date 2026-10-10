import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, ChevronDown, CircleAlert, ExternalLink, Info, ListChecks, Scale, ShieldAlert } from "lucide-react";
import { StatusBadge } from "../ui/StatusBadge";
import { Button } from "../ui/Button";
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
import type { CropEvaluation, FactorRead } from "../../types/crop";

const SCORED_ORDER = ["ph", "texture", "water", "season", "region"];

function ScoreBar({ score, coverage }: { score: number | null; coverage: number }) {
  const percent = score === null || score === undefined ? 0 : Math.round(score * 100);
  const coveragePercent = Math.round(coverage * 100);
  return (
    <div className="flex items-center gap-3">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-sunken">
        <div
          className="h-full rounded-full bg-brand-600 transition-[width] duration-300"
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className="w-16 text-right">
        <span className="text-sm font-bold text-ink">{formatScore(score)}</span>
      </div>
      <span className="hidden text-[11px] text-ink-muted sm:inline">
        {coveragePercent}% of weighed factors evaluated
      </span>
    </div>
  );
}

function FactorRow({ factor }: { factor: FactorRead }) {
  const info = FACTOR_STATUS_INFO[factor.status] ?? FACTOR_STATUS_INFO.not_required;
  return (
    <div className="rounded-card border border-border bg-surface-muted p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-sm font-semibold text-ink">
            {factor.label}
            {factor.is_essential && (
              <span className="rounded-full bg-brand-50 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-brand-700">
                Essential
              </span>
            )}
          </p>
          <p className="mt-0.5 text-xs text-ink-muted">
            {factor.status === "evaluated"
              ? `Field value: ${factorValueLabel(factor.factor, factor.input)} · needs: ${requirementText(factor.requirement)}`
              : factor.status === "missing_input"
                ? `Not answered yet · needs: ${requirementText(factor.requirement)}`
                : factor.status === "not_required"
                  ? "No documented requirement for this crop."
                  : requirementText(factor.requirement)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge tone={info.tone} dot>
            {info.label}
          </StatusBadge>
          <span
            className={cn(
              "rounded-lg px-2 py-1 text-sm font-bold",
              factor.score === null
                ? "bg-surface-sunken text-ink-muted"
                : factor.score >= 0.65
                  ? "bg-emerald-50 text-emerald-700"
                  : "bg-amber-50 text-amber-700"
            )}
          >
            {factor.score === null ? "—" : `${Math.round(factor.score * 100)}%`}
          </span>
        </div>
      </div>
      {factor.detail && (
        <p className="mt-2 text-xs leading-relaxed text-ink-soft">{factor.detail}</p>
      )}
    </div>
  );
}

function Risks({ risks }: { risks: CropEvaluation["risks"] }) {
  return (
    <div className="space-y-2">
      <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-muted">
        <ShieldAlert className="h-3.5 w-3.5" /> Forecast risks for this crop
      </h4>
      {risks.length === 0 ? (
        <p className="text-sm text-ink-muted">
          No active weather warnings in the current forecast.
        </p>
      ) : (
        <div className="space-y-2">
          {risks.map((risk, index) => (
            <div key={index} className="rounded-card border border-border bg-surface-muted p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="flex items-center gap-2 text-sm font-semibold text-ink">
                  {RISK_KIND_LABELS[risk.kind] ?? risk.kind}
                  <StatusBadge tone={RISK_SEVERITY_TONE[risk.severity] ?? "warning"} dot>
                    {risk.severity === "high" ? "High" : "Medium"} severity
                  </StatusBadge>
                </p>
                {risk.value !== null && (
                  <span className="text-xs font-semibold text-ink-soft">
                    {Math.round(risk.value)} {risk.unit}
                    {risk.period ? ` · ${risk.period}` : ""}
                  </span>
                )}
              </div>
              <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">{risk.title}</p>
              <p className="mt-0.5 text-xs leading-relaxed text-ink-muted">{risk.detail}</p>
              <p className="mt-1 text-[11px] text-ink-muted">
                Basis: {risk.basis} · Source: {risk.source}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ListBlock({
  title,
  icon,
  items,
  tone = "neutral",
}: {
  title: string;
  icon: React.ReactNode;
  items: string[];
  tone?: "neutral" | "amber" | "green";
}) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <h4
        className={cn(
          "flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-muted",
          tone === "amber" && "text-amber-700"
        )}
      >
        {icon} {title}
      </h4>
      <ul className="mt-2 space-y-1.5">
        {items.map((item, index) => (
          <li
            key={index}
            className={cn(
              "text-sm leading-relaxed text-ink-soft",
              tone === "amber" && "text-amber-800"
            )}
          >
            <span className="mr-1.5 text-ink-muted">•</span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CropResultCard({
  result,
  rank,
  defaultExpanded = false,
  onCompare,
}: {
  result: CropEvaluation;
  rank: number;
  defaultExpanded?: boolean;
  onCompare?: (cropId: number) => void;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const tone = CROP_STATUS_TONE[result.status] ?? "neutral";

  const scoredFactors = useMemo(
    () => SCORED_ORDER.map((factor) => result.factors?.[factor]).filter(Boolean),
    [result.factors]
  );
  const contextFactors = Object.values(result.context_factors ?? {});

  // Inputs the engine could not check for this crop, derived from the payload
  // (never hard-coded). Essential missing inputs are what make a crop
  // "needs more information" rather than genuinely unsuitable.
  const missingEssential = useMemo(
    () =>
      scoredFactors.filter(
        (factor) => factor.status === "missing_input" && factor.is_essential
      ),
    [scoredFactors]
  );

  return (
    <article className="overflow-hidden rounded-panel border border-border bg-surface shadow-card">
      <div className="flex items-center gap-2 px-4 py-4 sm:gap-3 sm:px-5">
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          className="flex min-w-0 flex-1 items-center gap-3 rounded-lg text-left transition-colors hover:bg-surface-muted"
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-surface-sunken text-sm font-bold text-ink-soft ring-1 ring-inset ring-border">
            {rank}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-display text-[15px] font-bold tracking-tight text-ink">{result.display_name}</h3>
              <span className="rounded-full bg-surface-sunken px-2 py-0.5 text-[11px] font-medium capitalize text-ink-muted">
                {result.category}
              </span>
            </div>
            {result.status === "needs_information" && missingEssential.length > 0 && (
              <p className="mt-1 flex flex-wrap items-center gap-1 text-[11px] font-medium text-amber-700">
                <CircleAlert className="h-3 w-3 shrink-0" />
                Missing to decide: {missingEssential.map((factor) => factor.label).join(", ")}
              </p>
            )}
            {result.preliminary && result.status !== "needs_information" && (
              <p className="mt-1 flex flex-wrap items-center gap-1 text-[11px] font-medium text-amber-700">
                <CircleAlert className="h-3 w-3 shrink-0" />
                Preliminary estimate - some requirements are not recorded yet.
              </p>
            )}
            <div className="mt-1.5 hidden sm:block">
              <ScoreBar score={result.score} coverage={result.coverage} />
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <div className="sm:hidden">
              <span className="font-display text-lg font-extrabold text-ink">{formatScore(result.score)}</span>
            </div>
            {result.preliminary && (
              <span className="hidden rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-800 sm:inline">
                Preliminary
              </span>
            )}
            <StatusBadge tone={tone} dot>
              {result.status_label}
            </StatusBadge>
            <ChevronDown
              className={cn("h-4 w-4 text-ink-muted transition-transform duration-200", expanded && "rotate-180")}
            />
          </div>
        </button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onCompare?.(result.crop_id)}
          disabled={!onCompare}
          leftIcon={<Scale className="h-4 w-4" />}
          className="shrink-0"
        >
          Compare
        </Button>
      </div>

      <div className="px-4 pb-1 sm:hidden sm:px-5">
        <ScoreBar score={result.score} coverage={result.coverage} />
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="space-y-5 border-t border-border px-4 py-5 sm:px-5">
              {result.description && (
                <p className="text-sm leading-relaxed text-ink-soft">{result.description}</p>
              )}

              <div>
                <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-muted">
                  <Info className="h-3.5 w-3.5" /> Factor comparison
                </h4>
                <div className="mt-2 grid gap-2.5 sm:grid-cols-2">
                  {scoredFactors.map((factor) => (
                    <FactorRow key={factor.factor} factor={factor} />
                  ))}
                </div>
              </div>

              {contextFactors.length > 0 && (
                <div>
                  <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-muted">
                    <CircleAlert className="h-3.5 w-3.5" /> Supporting context
                  </h4>
                  <ul className="mt-2 space-y-1.5">
                    {contextFactors.map((factor) => (
                      <li key={factor.factor} className="text-sm text-ink-soft">
                        <span className="font-medium text-ink">{factor.label}:</span>{" "}
                        {requirementText(factor.requirement)}
                        {factor.factor === "temperature" ||
                        factor.factor === "rainfall" ||
                        factor.factor === "duration"
                          ? ` ${factorUnit(factor.factor)}`
                          : ""}
                        {factor.requirement?.min_value !== undefined &&
                          factor.requirement?.min_value !== null &&
                          ` (${factor.requirement.explanation ?? "indicative"})`}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <Risks risks={result.risks ?? []} />

              <div className="grid gap-5 md:grid-cols-2">
                <ListBlock
                  title="Why this verdict"
                  icon={<CircleAlert className="h-3.5 w-3.5" />}
                  items={result.reasons ?? []}
                />
                <ListBlock
                  title="Suggested next steps"
                  icon={<ListChecks className="h-3.5 w-3.5" />}
                  items={result.next_steps ?? []}
                />
              </div>

              {(result.notes?.length ?? 0) > 0 && (
                <div className="rounded-card border border-amber-200 bg-amber-50 p-3">
                  <ListBlock
                    title="Notes"
                    icon={<AlertTriangle className="h-3.5 w-3.5" />}
                    items={result.notes}
                    tone="amber"
                  />
                </div>
              )}

              <p className="flex flex-wrap items-center gap-x-1.5 text-[11px] text-ink-muted">
                <span>Based on crop knowledge from {result.source}.</span>
                {result.source_url && (
                  <a
                    href={result.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-0.5 font-semibold text-brand-700 hover:text-brand-800"
                  >
                    View source <ExternalLink className="h-3 w-3" />
                  </a>
                )}
                {result.date_reviewed && <span>Reviewed {result.date_reviewed}.</span>}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </article>
  );
}