import { Clock, Eye } from "lucide-react";
import { Button } from "../ui/Button";
import { Skeleton } from "../ui/Skeleton";
import { seasonLabel } from "../../lib/crops";
import type { RecommendationSummary } from "../../types/crop";

function formatDateTime(value: string): string {
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

interface HistoryPanelProps {
  history: RecommendationSummary[];
  loading: boolean;
  onView: (batchId: string, createdLabel: string) => void;
  onRefresh: () => void;
}

export function HistoryPanel({ history, loading, onView, onRefresh }: HistoryPanelProps) {
  return (
    <section className="space-y-3 rounded-panel border border-border bg-surface p-5 shadow-card sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="flex items-center gap-2 text-base font-semibold text-ink">
            <Clock className="h-4 w-4 text-brand-700" /> Past assessments
          </h2>
          <p className="mt-0.5 text-xs text-ink-muted">
            Every run is stored with its inputs, so a past estimate can always be re-explained.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={onRefresh}>
          Refresh
        </Button>
      </div>

      {loading && history.length === 0 ? (
        <div className="space-y-2">
          {[...Array(2)].map((_, index) => (
            <Skeleton key={index} className="h-16 rounded-card" />
          ))}
        </div>
      ) : history.length === 0 ? (
        <p className="rounded-card border border-dashed border-border-strong bg-surface-muted p-4 text-sm text-ink-muted">
          No assessments yet. Run recommendations once and every past run will appear here.
        </p>
      ) : (
        <ul className="space-y-2">
          {history.map((batch) => {
            const label = `${seasonLabel(batch.season)} · ${formatDateTime(batch.created_at)}`;
            const total =
              batch.counts.suitable + batch.counts.needs_information + batch.counts.not_recommended;
            return (
              <li
                key={batch.batch_id}
                className="flex flex-wrap items-center gap-3 rounded-card border border-border bg-surface-muted p-3"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-ink">{label}</p>
                  <p className="mt-0.5 text-xs text-ink-muted">
                    {total} crops ·{" "}
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
                    {batch.top_crop ? ` · top: ${batch.top_crop}` : ""}
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
                  View
                </Button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}