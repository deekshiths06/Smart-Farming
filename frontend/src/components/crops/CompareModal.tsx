import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CircleAlert,
  CloudSun,
  FlaskConical,
  ListChecks,
  Scale,
  ShieldAlert,
  X,
} from "lucide-react";
import { Button } from "../ui/Button";
import { StatusBadge } from "../ui/StatusBadge";
import { cropsApi, cropsErrorMessage } from "../../services/crops";
import {
  CROP_STATUS_TONE,
  FACTOR_STATUS_INFO,
  formatScore,
  seasonLabel,
} from "../../lib/crops";
import { cn } from "../../lib/cn";
import type {
  CompareCellRead,
  CompareFactorRead,
  CompareRankedRead,
  CompareRead,
  CropEvaluation,
} from "../../types/crop";

const MAX_COMPARE = 3;

/**
 * The compare endpoint must return the full `CompareRead` object. Guard against
 * a legacy/partial payload (e.g. a bare array of crop evaluations) so a shape
 * mismatch shows a clear message instead of throwing inside render and taking
 * the whole page down with it.
 */
function isCompareRead(value: unknown): value is CompareRead {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const candidate = value as Partial<CompareRead>;
  return (
    !!candidate.context &&
    typeof candidate.context === "object" &&
    Array.isArray(candidate.ranking) &&
    Array.isArray(candidate.factors)
  );
}

function initialSelection(candidates: CropEvaluation[], seed: number[]): number[] {
  const available = new Set(candidates.map((crop) => crop.crop_id));
  const seeded = seed.filter((id) => available.has(id));
  const base =
    seeded.length > 0 ? seeded : candidates.slice(0, MAX_COMPARE).map((crop) => crop.crop_id);
  return [...new Set(base)].slice(0, MAX_COMPARE);
}

function CellScore({ score }: { score: number | null }) {
  if (score === null || score === undefined) {
    return <span className="text-xs font-semibold text-ink-muted">—</span>;
  }
  return (
    <span
      className={cn(
        "inline-block rounded-md px-1.5 py-0.5 text-xs font-bold",
        score >= 0.65 ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
      )}
    >
      {Math.round(score * 100)}%
    </span>
  );
}

function CellView({ cell }: { cell: CompareCellRead }) {
  const info = FACTOR_STATUS_INFO[cell.status] ?? FACTOR_STATUS_INFO.not_required;
  return (
    <div className="space-y-1.5">
      <StatusBadge tone={info.tone} dot>
        {info.label}
      </StatusBadge>
      <p className="text-xs leading-relaxed text-ink">
        <span className="font-semibold">{cell.value_label}</span>
        <span className="text-ink-muted"> · {cell.requirement_text}</span>
      </p>
      {cell.detail && <p className="text-[11px] leading-relaxed text-ink-muted">{cell.detail}</p>}
      <CellScore score={cell.score} />
    </div>
  );
}

function SectionTitle({
  icon,
  children,
}: {
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-muted">
      {icon} {children}
    </h3>
  );
}

function RankingEntry({ entry }: { entry: CompareRankedRead }) {
  const supporting = entry.supporting ?? [];
  const constraints = entry.constraints ?? [];
  const missing = entry.missing ?? [];
  return (
    <li className="rounded-card border border-border bg-surface-muted p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-surface-sunken text-xs font-bold text-ink-soft">
          {entry.rank}
        </span>
        <span className="text-sm font-semibold text-ink">{entry.display_name}</span>
        <StatusBadge tone={CROP_STATUS_TONE[entry.status] ?? "neutral"} dot>
          {entry.status_label}
        </StatusBadge>
        {entry.preliminary && (
          <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-800">
            Preliminary
          </span>
        )}
        <span className="ml-auto rounded-md bg-surface-sunken px-2 py-0.5 text-sm font-bold text-ink">
          {formatScore(entry.score)}
        </span>
      </div>
      <p className="mt-1 text-[11px] text-ink-muted">
        {Math.round((entry.coverage ?? 0) * 100)}% of weighed factors evaluated
      </p>
      <div className="mt-2 space-y-0.5 text-xs">
        {supporting.length > 0 && (
          <p className="text-emerald-700">
            <span className="font-semibold">Supports:</span> {supporting.join(" · ")}
          </p>
        )}
        {constraints.length > 0 && (
          <p className="text-red-700">
            <span className="font-semibold">Against:</span> {constraints.join(" · ")}
          </p>
        )}
        {missing.length > 0 && (
          <p className="text-amber-700">
            <span className="font-semibold">Not recorded:</span> {missing.join(", ")}
          </p>
        )}
      </div>
    </li>
  );
}

interface CompareModalProps {
  open: boolean;
  fieldId: number;
  fieldName: string;
  onClose: () => void;
  /** Evaluated crops from the field’s recommendation batch — only these can be compared. */
  candidates: CropEvaluation[];
  /** Optional crop ids to pre-select (e.g. from a card's Compare action). */
  seed?: number[];
}

export function CompareModal({
  open,
  fieldId,
  fieldName,
  onClose,
  candidates,
  seed = [],
}: CompareModalProps) {
  const [selected, setSelected] = useState<number[]>([]);
  const [comparison, setComparison] = useState<CompareRead | null>(null);
  const [view, setView] = useState<"pick" | "result">("pick");
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wasOpen = useRef(false);

  // Only re-initialise on the false -> true transition, and only when a new
  // seed is supplied. Simply closing and reopening keeps the current selection
  // and the last comparison so nothing the farmer did is lost.
  useEffect(() => {
    if (open && !wasOpen.current) {
      setError(null);
      if (seed.length > 0) {
        setSelected(initialSelection(candidates, seed));
        setComparison(null);
        setView("pick");
      } else {
        setSelected((current) => {
          const stillValid = current.filter((id) =>
            candidates.some((crop) => crop.crop_id === id)
          );
          return stillValid.length > 0 ? stillValid : initialSelection(candidates, seed);
        });
      }
    }
    wasOpen.current = open;
  }, [open, candidates, seed]);

  const toggle = (cropId: number) => {
    setSelected((current) => {
      if (current.includes(cropId)) return current.filter((id) => id !== cropId);
      if (current.length >= MAX_COMPARE) return current;
      return [...current, cropId];
    });
  };

  const runCompare = async () => {
    setError(null);
    setComparing(true);
    try {
      const data = await cropsApi.compare(fieldId, selected);
      if (!isCompareRead(data)) {
        setComparison(null);
        setError(
          "The comparison service returned an unexpected response. Please close this and try again."
        );
        return;
      }
      setComparison(data);
      setView("result");
    } catch (err) {
      setError(cropsErrorMessage(err, "The comparison could not be run right now."));
    } finally {
      setComparing(false);
    }
  };

  const selectedScale = (): string => {
    if (selected.length === 0) return "Select at least one crop";
    const label = `${selected.length} crop${selected.length > 1 ? "s" : ""} selected`;
    return selected.length < 2 ? `${label} — add a second to see what differs.` : label;
  };

  if (typeof document === "undefined") return null;

  const ranking = comparison?.ranking ?? [];
  const factors = comparison?.factors ?? [];
  const differences = comparison?.differences ?? [];
  const rankChangers = comparison?.rank_changers ?? [];
  const infoToCollect = comparison?.info_to_collect ?? [];

  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[1000] flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          role="dialog"
          aria-modal="true"
          aria-label="Compare crops"
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
            className="relative flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-panel border border-border bg-surface shadow-pop"
          >
            <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
                  <Scale className="h-5 w-5" />
                </span>
                <div>
                  <h2 className="text-lg font-semibold text-ink">Compare crops</h2>
                  <p className="mt-0.5 text-sm text-ink-muted">
                    Against “{fieldName}” · pick {MAX_COMPARE} crops and see why one suits it best.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close"
                className="rounded-md p-1.5 text-ink-muted hover:bg-surface-sunken"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="thin-scroll flex-1 overflow-y-auto p-5">
              {error && (
                <div className="mb-4 rounded-card border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  {error}
                </div>
              )}

              {view === "pick" ? (
                <div>
                  <p className="text-sm text-ink-soft">
                    Only crops from this field’s recommendations can be compared — everything here
                    comes from the same evaluation, so the comparison is honest, not invented.
                  </p>

                  {candidates.length === 0 ? (
                    <div className="mt-4 rounded-card border border-border bg-surface-muted p-6 text-sm text-ink-muted">
                      Run recommendations first to get crops you can compare.
                    </div>
                  ) : (
                    <div className="mt-4 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                      {candidates.map((crop) => {
                        const active = selected.includes(crop.crop_id);
                        return (
                          <button
                            key={crop.crop_id}
                            type="button"
                            onClick={() => toggle(crop.crop_id)}
                            aria-pressed={active}
                            className={cn(
                              "rounded-card border p-3 text-left transition-colors",
                              active
                                ? "border-brand-400 bg-brand-50 ring-1 ring-brand-500"
                                : "border-border bg-surface-muted hover:border-border-strong"
                            )}
                          >
                            <span className="flex items-center justify-between gap-2">
                              <span className="text-sm font-semibold text-ink">
                                {crop.display_name}
                              </span>
                              <StatusBadge tone={CROP_STATUS_TONE[crop.status] ?? "neutral"} dot>
                                {crop.status_label}
                              </StatusBadge>
                            </span>
                            <span className="mt-1 block text-[11px] text-ink-muted">
                              {crop.category} · score {formatScore(crop.score)}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {selected.length === MAX_COMPARE && (
                    <p className="mt-3 text-xs text-ink-muted">
                      Maximum {MAX_COMPARE} crops can be compared at once.
                    </p>
                  )}
                </div>
              ) : comparison ? (
                <div className="space-y-6">
                  <div className="flex flex-wrap items-center gap-2 text-[11px] text-ink-muted">
                    <span className="rounded-lg bg-surface-sunken px-2.5 py-1.5 capitalize">
                      Season · {seasonLabel(comparison.context?.season)}
                    </span>
                    <span className="inline-flex items-center gap-1.5 rounded-lg bg-surface-sunken px-2.5 py-1.5">
                      <FlaskConical className="h-3.5 w-3.5" />
                      {comparison.context?.soil?.has_measurement
                        ? "Soil test compared"
                        : "No soil test recorded"}
                    </span>
                    <span className="inline-flex items-center gap-1.5 rounded-lg bg-surface-sunken px-2.5 py-1.5">
                      <CloudSun className="h-3.5 w-3.5" />
                      {comparison.context?.weather?.available
                        ? "Live forecast included as risk context"
                        : "Live weather not available"}
                    </span>
                  </div>

                  {comparison.preliminary_note && (
                    <div className="flex items-start gap-2 rounded-card border border-amber-200 bg-amber-50 p-4 text-sm leading-relaxed text-amber-800">
                      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                      <p>{comparison.preliminary_note}</p>
                    </div>
                  )}

                  <section className="space-y-2">
                    <SectionTitle icon={<ListChecks className="h-3.5 w-3.5" />}>
                      Ranking on current evidence
                    </SectionTitle>
                    <ol className="space-y-2">
                      {ranking.map((entry) => (
                        <RankingEntry key={entry.crop_id} entry={entry} />
                      ))}
                    </ol>
                  </section>

                  {differences.length > 0 && (
                    <section className="space-y-2">
                      <SectionTitle icon={<CircleAlert className="h-3.5 w-3.5" />}>
                        Why this order
                      </SectionTitle>
                      <ol className="space-y-1.5">
                        {differences.map((line, index) => (
                          <li
                            key={index}
                            className="flex items-start gap-2 text-sm leading-relaxed text-ink-soft"
                          >
                            <span className="mt-0.5 text-ink-muted">{index + 1}.</span>
                            {line}
                          </li>
                        ))}
                      </ol>
                    </section>
                  )}

                  <section className="space-y-2">
                    <SectionTitle icon={<Scale className="h-3.5 w-3.5" />}>
                      Side-by-side factors
                    </SectionTitle>
                    <p className="text-xs text-ink-soft">
                      Every value is the field’s recorded value versus the crop’s documented
                      requirement — nothing is guessed.
                    </p>

                    {/* Desktop matrix */}
                    <div className="hidden overflow-x-auto border border-border rounded-card md:block">
                      <table className="w-full border-separate border-spacing-0 text-left">
                        <thead>
                          <tr className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                            <th className="border-b border-border bg-surface-muted px-3 py-2.5">
                              Factor
                            </th>
                            {ranking.map((entry) => (
                              <th
                                key={entry.crop_id}
                                className="border-b border-l border-border bg-surface-muted px-3 py-2.5"
                              >
                                {entry.rank}. {entry.display_name}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {factors.map((row) => (
                            <tr key={row.factor} className="align-top">
                              <td className="border-b border-border px-3 py-3">
                                <p className="text-sm font-semibold text-ink">{row.label}</p>
                                <p className="mt-0.5 text-[11px] leading-relaxed text-ink-muted">
                                  {row.explanation}
                                </p>
                              </td>
                              {row.cells.map((cell) => (
                                <td
                                  key={cell.crop_id}
                                  className="border-b border-l border-border px-3 py-3 align-top"
                                >
                                  <CellView cell={cell} />
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Mobile factor cards */}
                    <div className="space-y-3 md:hidden">
                      {factors.map((row) => (
                        <MobileFactorRow key={row.factor} row={row} ranking={ranking} />
                      ))}
                    </div>
                  </section>

                  {rankChangers.length > 0 && (
                    <section className="space-y-2">
                      <SectionTitle icon={<ShieldAlert className="h-3.5 w-3.5" />}>
                        What could change the order
                      </SectionTitle>
                      <ul className="space-y-1.5">
                        {rankChangers.map((line, index) => (
                          <li
                            key={index}
                            className="flex items-start gap-2 text-sm leading-relaxed text-ink-soft"
                          >
                            <span className="mt-0.5 text-ink-muted">•</span>
                            {line}
                          </li>
                        ))}
                      </ul>
                    </section>
                  )}

                  <section className="space-y-2">
                    <SectionTitle icon={<FlaskConical className="h-3.5 w-3.5" />}>
                      Information to record next
                    </SectionTitle>
                    {infoToCollect.length === 0 ? (
                      <p className="text-sm text-ink-soft">
                        Nothing missing — every documented requirement was checked for the crops
                        you compared.
                      </p>
                    ) : (
                      <ul className="space-y-1.5">
                        {infoToCollect.map((item) => (
                          <li
                            key={item.input}
                            className="flex items-start gap-2 text-sm leading-relaxed text-ink-soft"
                          >
                            <ListChecks className="mt-0.5 h-4 w-4 shrink-0 text-brand-700" />
                            <span>
                              <span className="font-semibold capitalize text-ink">
                                {item.input.replace("_", " ")}
                              </span>{" "}
                              — {item.action}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </section>

                  <p className="text-xs leading-relaxed text-ink-muted">{comparison.disclaimer}</p>
                </div>
              ) : (
                <div className="grid gap-3">
                  {[...Array(4)].map((_, index) => (
                    <div key={index} className="h-14 animate-pulse rounded-card bg-surface-sunken" />
                  ))}
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-5 py-4">
              <p className="text-xs text-ink-muted">{view === "pick" ? selectedScale() : "Return to the recommendations any time — nothing is lost."}</p>
              <div className="flex flex-wrap items-center gap-2">
                {view === "result" && (
                  <Button variant="outline" onClick={() => setView("pick")} leftIcon={<ArrowLeft className="h-4 w-4" />}>
                    Change crops
                  </Button>
                )}
                <Button variant="outline" onClick={onClose}>
                  Back to rankings
                </Button>
                {view === "pick" && (
                  <Button
                    onClick={() => void runCompare()}
                    loading={comparing}
                    disabled={selected.length === 0 || candidates.length === 0}
                    rightIcon={<ArrowRight className="h-4 w-4" />}
                  >
                    Compare
                  </Button>
                )}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  );
}

function MobileFactorRow({
  row,
  ranking,
}: {
  row: CompareFactorRead;
  ranking: CompareRankedRead[];
}) {
  return (
    <div className="rounded-card border border-border bg-surface-muted p-3">
      <p className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-semibold text-ink">{row.label}</span>
        {row.compared ? (
          <span className="text-[10px] font-bold uppercase tracking-wide text-emerald-700">
            Compared
          </span>
        ) : (
          <span className="text-[10px] font-bold uppercase tracking-wide text-amber-700">
            Not recorded
          </span>
        )}
      </p>
      <p className="mt-1 text-xs leading-relaxed text-ink-muted">{row.explanation}</p>
      <div className="mt-2 space-y-1.5">
        {(row.cells ?? []).map((cell) => {
          const crop = ranking.find((entry) => entry.crop_id === cell.crop_id);
          return (
            <div
              key={cell.crop_id}
              className="flex items-start justify-between gap-2 border-t border-border pt-1.5"
            >
              <div className="min-w-0">
                <p className="text-xs font-semibold text-ink">{crop?.display_name ?? cell.crop_id}</p>
                <p className="text-[11px] leading-relaxed text-ink-soft">
                  {cell.value_label} · {cell.requirement_text}
                </p>
                <p className="mt-0.5 text-[10px] text-ink-muted">
                  {FACTOR_STATUS_INFO[cell.status]?.label ?? cell.status}
                  {cell.detail ? ` — ${cell.detail}` : ""}
                </p>
              </div>
              <CellScore score={cell.score} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
