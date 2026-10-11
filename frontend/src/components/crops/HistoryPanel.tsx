import { useState, type ReactNode } from "react";
import {
  CalendarDays,
  ChevronDown,
  Clock,
  Eye,
  History,
  MapPin,
  RefreshCw,
  Trophy,
} from "lucide-react";
import { Button } from "../ui/Button";
import { Skeleton } from "../ui/Skeleton";
import { cn } from "../../lib/cn";
import { seasonLabel } from "../../lib/crops";
import type { RecommendationSummary } from "../../types/crop";

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "Date not recorded";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function seasonText(season: string | null | undefined): string {
  if (!season) return "Season not recorded";
  return seasonLabel(season);
}

function assessmentLabel(batch: RecommendationSummary): string {
  return `${seasonText(batch.season)} · ${formatDateTime(batch.created_at)}`;
}

function CountChips({ counts }: { counts: RecommendationSummary["counts"] }) {
  const total = counts.suitable + counts.needs_information + counts.not_recommended;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-xs font-semibold text-ink-soft">{total} crops</span>
      <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200">
        {counts.suitable} suitable
      </span>
      <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700 ring-1 ring-amber-200">
        {counts.needs_information} need more info
      </span>
      <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-semibold text-red-700 ring-1 ring-red-200">
        {counts.not_recommended} not recommended
      </span>
    </div>
  );
}

function Meta({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-start gap-2">
      <span className="mt-0.5 text-brand-700">{icon}</span>
      <div className="min-w-0">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">{label}</p>
        <p className="truncate text-sm font-medium text-ink" title={value}>
          {value}
        </p>
      </div>
    </div>
  );
}

interface PastAssessmentsProps {
  history: RecommendationSummary[];
  loading: boolean;
  fieldName: string | null | undefined;
  location: string | null | undefined;
  onView: (batchId: string, createdLabel: string) => void;
  onRefresh: () => void;
}

export function PastAssessments({
  history,
  loading,
  fieldName,
  location,
  onView,
  onRefresh,
}: PastAssessmentsProps) {
  const [previousOpen, setPreviousOpen] = useState(false);

  const latest = history[0];
  const previous = history.slice(1);
  const fieldLabel = fieldName
    ? location
      ? `${fieldName} · ${location}`
      : fieldName
    : location
      ? location
      : "Field not recorded";

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="flex items-center gap-2 text-base font-semibold text-ink">
            <Clock className="h-4 w-4 text-brand-700" /> Past assessments
          </h2>
          <p className="mt-0.5 text-xs text-ink-muted">
            Every run is stored with its inputs, so a past estimate can always be re-explained.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          leftIcon={<RefreshCw className="h-4 w-4" />}
          onClick={onRefresh}
          disabled={loading}
        >
          Refresh
        </Button>
      </div>

      {loading && history.length === 0 ? (
        <div className="space-y-3">
          <Skeleton className="h-56 rounded-panel" />
          <Skeleton className="h-14 rounded-panel" />
        </div>
      ) : !latest ? (
        <div className="rounded-panel border border-dashed border-border-strong bg-surface p-8 text-center">
          <p className="text-sm font-semibold text-ink">No saved assessments yet</p>
          <p className="mt-1 text-sm text-ink-muted">
            Run a new assessment and it will be stored here with its exact inputs, so you can
            always reopen it.
          </p>
        </div>
      ) : (
        <>
          <article className="rounded-panel border border-brand-200 bg-brand-50/60 p-4 shadow-card sm:p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white">
                  <Clock className="h-5 w-5" />
                </span>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-bold tracking-tight text-ink">
                      Latest assessment
                    </h3>
                    <span className="rounded-full bg-brand-600 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
                      Latest
                    </span>
                  </div>
                  <p className="mt-0.5 text-sm text-ink-muted">
                    The most recent run stored for this field.
                  </p>
                </div>
              </div>
              <Button
                leftIcon={<Eye className="h-4 w-4" />}
                onClick={() => onView(latest.batch_id, assessmentLabel(latest))}
              >
                View Results
              </Button>
            </div>

            <div className="mt-4 grid gap-3 rounded-card border border-border bg-surface p-3 sm:grid-cols-2 lg:grid-cols-4">
              <Meta
                icon={<CalendarDays className="h-4 w-4" />}
                label="Date"
                value={formatDateTime(latest.created_at)}
              />
              <Meta
                icon={<MapPin className="h-4 w-4" />}
                label="Field / location"
                value={fieldLabel}
              />
              <Meta
                icon={<CalendarDays className="h-4 w-4" />}
                label="Season"
                value={seasonText(latest.season)}
              />
              <Meta
                icon={<Trophy className="h-4 w-4" />}
                label="Top-ranked crop"
                value={latest.top_crop ?? "—"}
              />
            </div>

            <div className="mt-3">
              <CountChips counts={latest.counts} />
            </div>
          </article>

          {previous.length > 0 && (
            <div className="overflow-hidden rounded-panel border border-border bg-surface shadow-card">
              <button
                type="button"
                onClick={() => setPreviousOpen((open) => !open)}
                aria-expanded={previousOpen}
                className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left transition-colors hover:bg-surface-muted"
              >
                <span className="flex items-center gap-2 text-sm font-semibold text-ink">
                  <History className="h-4 w-4 text-brand-700" />
                  Previous assessments
                  <span className="rounded-full bg-surface-sunken px-2 py-0.5 text-xs font-semibold text-ink-soft">
                    {previous.length}
                  </span>
                </span>
                <ChevronDown
                  className={cn(
                    "h-4 w-4 shrink-0 text-ink-muted transition-transform",
                    previousOpen && "rotate-180"
                  )}
                />
              </button>

              {previousOpen && (
                <ul className="space-y-2 border-t border-border p-3">
                  {previous.map((batch) => {
                    const label = assessmentLabel(batch);
                    return (
                      <li
                        key={batch.batch_id}
                        className="flex flex-wrap items-center gap-3 rounded-card border border-border bg-surface-muted p-3"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-ink">
                            {formatDateTime(batch.created_at)}
                          </p>
                          <p className="mt-0.5 text-xs text-ink-muted">
                            {seasonText(batch.season)}
                            {batch.top_crop ? ` · top: ${batch.top_crop}` : ""}
                          </p>
                          <p className="mt-1 text-xs text-ink-muted">
                            {batch.counts.suitable + batch.counts.needs_information + batch.counts.not_recommended}{" "}
                            crops ·{" "}
                            <span className="font-semibold text-emerald-700">
                              {batch.counts.suitable} suitable
                            </span>
                            {" · "}
                            <span className="font-semibold text-amber-700">
                              {batch.counts.needs_information} need more info
                            </span>
                            {" · "}
                            <span className="font-semibold text-red-700">
                              {batch.counts.not_recommended} not recommended
                            </span>
                          </p>
                          <p className="mt-0.5 font-mono text-[10px] text-ink-muted">
                            engine v{batch.engine_version}
                          </p>
                        </div>
                        <Button
                          variant="secondary"
                          size="sm"
                          leftIcon={<Eye className="h-4 w-4" />}
                          onClick={() => onView(batch.batch_id, label)}
                        >
                          View Results
                        </Button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
