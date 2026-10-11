import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { CalendarDays, FlaskConical, X } from "lucide-react";
import { Skeleton } from "../ui/Skeleton";
import { cropsApi } from "../../services/crops";
import { formatScore, seasonLabel } from "../../lib/crops";
import { CropResultCard } from "./CropResultCard";
import { CropDetailModal } from "./CropDetailModal";
import { formatSoilDate } from "../../lib/soil";
import { WATER_AVAILABILITY_LABELS, WATER_SOURCE_LABELS } from "../../lib/labels";
import type { CropEvaluation, RecommendationRead } from "../../types/crop";

const STATUS_ORDER = { suitable: 0, needs_information: 1, not_recommended: 2 } as const;

function sortRows(rows: RecommendationRead[]): RecommendationRead[] {
  return [...rows].sort((a, b) => {
    const aOrder = STATUS_ORDER[a.status] ?? 3;
    const bOrder = STATUS_ORDER[b.status] ?? 3;
    if (aOrder !== bOrder) return aOrder - bOrder;
    return (b.score ?? -1) - (a.score ?? -1);
  });
}

interface RecommendationDetailModalProps {
  open: boolean;
  fieldId: number;
  batchId: string;
  label: string;
  onClose: () => void;
}

export function RecommendationDetailModal({
  open,
  fieldId,
  batchId,
  label,
  onClose,
}: RecommendationDetailModalProps) {
  const [rows, setRows] = useState<RecommendationRead[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<CropEvaluation | null>(null);

  useEffect(() => {
    if (!open) return;
    setRows(null);
    setError(null);
    setSelected(null);
    setLoading(true);
    cropsApi
      .batch(fieldId, batchId)
      .then((list) => setRows(sortRows(list)))
      .catch(() => setError("This past assessment could not be loaded."))
      .finally(() => setLoading(false));
  }, [open, fieldId, batchId]);

  if (typeof document === "undefined") return null;

  const snapshot = rows?.[0]?.input_snapshot;
  const snapshotField = (snapshot?.field ?? {}) as Record<string, unknown>;
  const originalFieldName =
    typeof snapshotField.field_name === "string" ? snapshotField.field_name : null;
  const originalLocation =
    [snapshotField.district, snapshotField.state]
      .filter((part): part is string => typeof part === "string" && part.length > 0)
      .join(", ") || null;
  const originalWaterSource =
    typeof snapshotField.water_source === "string" ? snapshotField.water_source : null;
  const originalWaterAvailability =
    typeof snapshotField.water_availability === "string"
      ? snapshotField.water_availability
      : null;
  const hasOriginalInputs =
    Boolean(snapshot) &&
    (originalFieldName !== null ||
      originalLocation !== null ||
      originalWaterSource !== null ||
      originalWaterAvailability !== null);

  return createPortal(
    <>
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
          aria-label={`Past assessment ${label}`}
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
            className="thin-scroll relative flex max-h-[90vh] w-full max-w-3xl flex-col overflow-y-auto rounded-panel border border-border bg-surface shadow-pop"
          >
            <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
                  <CalendarDays className="h-5 w-5" />
                </span>
                <div>
                  <h2 className="text-lg font-semibold text-ink">Past assessment</h2>
                  <p className="mt-0.5 text-sm text-ink-muted">{label}</p>
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

            <div className="flex-1 space-y-4 overflow-y-auto p-5">
              {error && (
                <div className="rounded-card border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  {error}
                </div>
              )}

              {loading && !rows ? (
                <div className="space-y-4">
                  {[...Array(3)].map((_, index) => (
                    <Skeleton key={index} className="h-28 rounded-panel" />
                  ))}
                </div>
              ) : (
                rows && (
                  <>
                    <div className="flex flex-wrap items-center gap-2 rounded-card border border-border bg-surface-muted p-3 text-xs text-ink-muted">
                      <span className="inline-flex items-center gap-1.5 font-semibold text-ink">
                        <CalendarDays className="h-3.5 w-3.5" />
                        {seasonLabel(snapshot?.season ?? null)}
                      </span>
                      {snapshot && (
                        <>
                          <span>·</span>
                          <span>Referenced {snapshot.reference_date}</span>
                          <span>·</span>
                          <span className="inline-flex items-center gap-1">
                            <FlaskConical className="h-3.5 w-3.5" />
                            {snapshot.soil.has_measurement
                              ? `Soil tested ${formatSoilDate(snapshot.soil.tested_on)}`
                              : "No soil test at the time"}
                          </span>
                          <span>·</span>
                          <span className="inline-flex items-center gap-1.5">
                            <span
                              className={`h-2 w-2 rounded-full ${
                                snapshot.weather.available ? "bg-emerald-500" : "bg-amber-400"
                              }`}
                            />
                            {snapshot.weather.available
                              ? "Live weather included"
                              : "Live weather not available"}
                          </span>
                          <span className="ml-auto font-mono">
                            engine v{snapshot.engine_version}
                          </span>
                        </>
                      )}
                    </div>

                    {hasOriginalInputs && (
                      <div className="rounded-card border border-border bg-surface p-3">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                          Original inputs
                        </p>
                        <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
                          <div className="flex items-baseline gap-2">
                            <dt className="text-ink-muted">Field</dt>
                            <dd className="min-w-0 truncate font-medium text-ink">
                              {originalFieldName ?? "—"}
                            </dd>
                          </div>
                          <div className="flex items-baseline gap-2">
                            <dt className="text-ink-muted">Location</dt>
                            <dd className="min-w-0 truncate font-medium text-ink">
                              {originalLocation ?? "—"}
                            </dd>
                          </div>
                          <div className="flex items-baseline gap-2">
                            <dt className="text-ink-muted">Water source</dt>
                            <dd className="min-w-0 truncate font-medium text-ink">
                              {originalWaterSource
                                ? WATER_SOURCE_LABELS[originalWaterSource] ??
                                  originalWaterSource
                                : "—"}
                            </dd>
                          </div>
                          <div className="flex items-baseline gap-2">
                            <dt className="text-ink-muted">Water availability</dt>
                            <dd className="min-w-0 truncate font-medium text-ink">
                              {originalWaterAvailability
                                ? WATER_AVAILABILITY_LABELS[originalWaterAvailability] ??
                                  originalWaterAvailability
                                : "—"}
                            </dd>
                          </div>
                        </dl>
                      </div>
                    )}

                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                      {rows.map((row) => (
                        <CropResultCard
                          key={row.id}
                          result={row.result}
                          onViewDetails={setSelected}
                        />
                      ))}
                    </div>

                    <div className="flex items-center justify-end gap-2">
                      <span className="text-xs text-ink-muted">
                        {rows.length} crops · best score{" "}
                        {rows[0]?.score !== null && rows[0]?.score !== undefined
                          ? `${formatScore(rows[0].score)} (${rows[0].display_name})`
                          : "—"}
                      </span>
                    </div>
                  </>
                )
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
      </AnimatePresence>
      <CropDetailModal
        open={selected !== null}
        crop={selected}
        config={snapshot?.scoring ?? null}
        soil={snapshot?.soil ?? null}
        weather={snapshot?.weather ?? null}
        onClose={() => setSelected(null)}
      />
    </>,
    document.body
  );
}