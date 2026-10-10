import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  CloudSun,
  FlaskConical,
  Info,
  Scale,
  Sprout,
  Wheat,
  Zap,
} from "lucide-react";
import { PageHeader } from "../components/ui/PageHeader";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { Skeleton } from "../components/ui/Skeleton";
import { StatusBadge } from "../components/ui/StatusBadge";
import { CropResultCard } from "../components/crops/CropResultCard";
import { CompareModal } from "../components/crops/CompareModal";
import { HistoryPanel } from "../components/crops/HistoryPanel";
import { RecommendationDetailModal } from "../components/crops/RecommendationDetailModal";
import { useFields } from "../hooks/useFields";
import { useCrops } from "../hooks/useCrops";
import { cropsErrorMessage } from "../services/crops";
import { landStructure } from "../lib/labels";
import { formatSoilDate } from "../lib/soil";
import { seasonLabel } from "../lib/crops";
import { cn } from "../lib/cn";

function ContextTile({
  icon,
  title,
  children,
  tone = "neutral",
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  tone?: "neutral" | "success" | "warning";
}) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-card border p-4",
        tone === "warning"
          ? "border-amber-200 bg-amber-50"
          : tone === "success"
            ? "border-emerald-200 bg-emerald-50/60"
            : "border-border bg-surface-muted"
      )}
    >
      <span
        className={cn(
          "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          tone === "warning"
            ? "bg-amber-100 text-amber-700"
            : tone === "success"
              ? "bg-emerald-100 text-emerald-700"
              : "bg-surface-sunken text-ink-muted"
        )}
      >
        {icon}
      </span>
      <div className="min-w-0">
        <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">{title}</p>
        <div className="mt-1 text-sm leading-relaxed text-ink-soft">{children}</div>
      </div>
    </div>
  );
}

export default function CropRecommendations() {
  const { fields, loading: fieldsLoading, selectedField } = useFields();
  const {
    batch,
    history,
    loading,
    generating,
    error,
    generate,
    reloadHistory,
  } = useCrops(selectedField?.id);

  const [compareOpen, setCompareOpen] = useState(false);
  const [compareSeed, setCompareSeed] = useState<number[]>([]);
  const [runError, setRunError] = useState<string | null>(null);
  const [detail, setDetail] = useState<{ batchId: string; label: string } | null>(null);

  const openCompare = (seed: number[]) => {
    setCompareSeed(seed);
    setCompareOpen(true);
  };

  const handleRun = async () => {
    setRunError(null);
    if (!selectedField) return;
    try {
      await generate();
    } catch (err) {
      setRunError(
        cropsErrorMessage(err, "The recommendation could not be generated right now.")
      );
    }
  };

  const stats = useMemo(() => {
    if (!batch) return null;
    return batch.results.reduce(
      (acc, result) => {
        acc[result.status] = (acc[result.status] ?? 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );
  }, [batch]);

  // Which inputs the engine could not check for at least one crop. Missing
  // inputs never block a verdict now: each crop is scored on the evidence that
  // exists and flagged preliminary. Derived from the payload so the wording
  // always matches what the engine actually reported.
  const missingInputs = useMemo(() => {
    if (!batch) return null;
    const essential = new Map<string, string>();
    const optional = new Set<string>();
    for (const result of batch.results) {
      for (const factor of Object.values(result.factors ?? {})) {
        if (factor.status !== "missing_input") continue;
        if (factor.is_essential) essential.set(factor.factor, factor.label);
        else optional.add(factor.label);
      }
    }
    const all = [...essential.values(), ...optional.values()];
    return { essential: [...essential.values()], optional: [...optional.values()], all };
  }, [batch]);

  if (fieldsLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-20 rounded-panel" />
        <div className="grid gap-4 sm:grid-cols-2">
          {[...Array(4)].map((_, index) => (
            <Skeleton key={index} className="h-40 rounded-card" />
          ))}
        </div>
      </div>
    );
  }

  if (fields.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Crop Recommendations"
          description="Compare every crop in the knowledge base against your field and see a transparent suitability estimate."
          icon={<Wheat className="h-5 w-5" />}
        />
        <EmptyState
          icon={<Wheat className="h-8 w-8" />}
          title="Add a field to get crop recommendations"
          description="Recommendations are estimated for a real field — its location, water and recorded soil. Create your first field to see which crops suit it."
          action={
            <Link to="/fields/create">
              <Button rightIcon={<Sprout className="h-4 w-4" />}>Create your first field</Button>
            </Link>
          }
        />
      </div>
    );
  }

  const soilExplains =
    !batch?.soil.has_measurement
      ? "No soil measurement was recorded for this field, so pH and soil texture were not compared for any crop."
      : batch.soil.is_stale
        ? `The soil test on file is older than the scoring limit, so pH and texture were not compared.`
        : batch.soil.is_future
          ? "The soil test on file is dated in the future, so it was not used for scoring."
          : null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Crop Recommendations"
        description="Every crop is scored against your field's recorded soil, water and location, plus the live forecast as risk context."
        icon={<Wheat className="h-5 w-5" />}
        actions={
          <>
            <Button
              variant="outline"
              onClick={() => openCompare([])}
              disabled={!selectedField || !batch}
              leftIcon={<Scale className="h-4 w-4" />}
            >
              Compare crops
            </Button>
            <Button
              onClick={() => void handleRun()}
              loading={generating}
              disabled={!selectedField}
              leftIcon={<Zap className="h-4 w-4" />}
            >
              {batch ? "Re-run recommendations" : "Run recommendations"}
            </Button>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2 text-sm text-ink-muted">
        <span className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-2.5 py-1.5 shadow-card">
          <Wheat className="h-3.5 w-3.5 text-brand-700" />
          {selectedField?.field_name}
        </span>
        <span className="rounded-lg bg-surface-sunken px-2.5 py-1.5">
          {landStructure(
            selectedField as unknown as {
              locality?: string | null;
              sub_district?: string | null;
              district?: string | null;
              state?: string | null;
              country?: string | null;
            }
          )}
        </span>
        <span className="text-xs">Change field from the selector in the top bar.</span>
      </div>

      {(error || runError) && (
        <ErrorAlert
          title="Recommendations could not be loaded"
          message={runError ?? error ?? ""}
          onRetry={() => void handleRun()}
        />
      )}

      {!batch && !loading ? (
        <EmptyState
          icon={<Zap className="h-8 w-8" />}
          title={`What suits ${selectedField?.field_name}?`}
          description="Run the assessment to score every crop in the knowledge base against this field. Anything ANNADATA does not know — soil, water — is marked clearly instead of guessed."
          action={
            <Button onClick={() => void handleRun()} loading={generating}>
              Run recommendations now
            </Button>
          }
        />
      ) : !batch ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {[...Array(4)].map((_, index) => (
            <Skeleton key={index} className="h-40 rounded-card" />
          ))}
        </div>
      ) : (
        <>
          {/* Input context */}
          <section className="grid gap-4 md:grid-cols-3">
            <ContextTile
              icon={<FlaskConical className="h-4 w-4" />}
              title="Soil"
              tone={batch.soil.has_measurement ? "success" : "warning"}
            >
              {batch.soil.has_measurement ? (
                <p>
                  Compared against the soil test from{" "}
                  <span className="font-semibold text-ink">
                    {formatSoilDate(batch.soil.tested_on)}
                  </span>
                  .
                  {(batch.soil.is_stale || batch.soil.is_future) && (
                    <span className="mt-1 block text-amber-700">But it was excluded from scoring (see note below).</span>
                  )}
                </p>
              ) : (
                <p>
                  No soil test recorded for this field.{" "}
                  <Link to="/soil" className="font-semibold text-amber-900 underline-offset-2 hover:underline">
                    Add one in Soil Intelligence
                  </Link>{" "}
                  so pH and texture can be compared.
                </p>
              )}
            </ContextTile>

            <ContextTile
              icon={<CloudSun className="h-4 w-4" />}
              title="Weather"
              tone={batch.weather.available ? "success" : "warning"}
            >
              {batch.weather.available ? (
                <p>
                  Live {batch.weather.source} forecast included as risk context
                  {batch.weather.observed_at && (
                    <>
                      {" "}
                      observed {new Date(batch.weather.observed_at).toLocaleString()}.
                    </>
                  )}
                </p>
              ) : (
                <p>
                  {batch.weather.reason ?? "Live weather was not available."}{" "}
                  <Link to="/weather" className="font-semibold text-amber-900 underline-offset-2 hover:underline">
                    View weather
                  </Link>
                </p>
              )}
            </ContextTile>

            <ContextTile
              icon={<Info className="h-4 w-4" />}
              title={`Season · ${seasonLabel(batch.season)}`}
            >
              <p>Generated {new Date(batch.generated_at).toLocaleString()}.</p>
              <p className="mt-0.5 text-xs text-ink-muted">
                Weights, threshold and essential factors come from the active scoring configuration.
              </p>
            </ContextTile>
          </section>

          {soilExplains && (
            <div className="flex items-start gap-2 rounded-card border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <p>
                {soilExplains}
              </p>
            </div>
          )}

          {missingInputs && missingInputs.all.length > 0 && (
            <section className="rounded-panel border border-amber-200 bg-amber-50 p-4 sm:p-5">
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                <div className="text-sm leading-relaxed text-amber-800">
                  <p className="font-semibold">
                    Some field inputs are not recorded yet, so crops are scored as
                    preliminary estimates.
                  </p>
                  <p className="mt-1">
                    No crop is refused or zeroed for missing data: each one is scored on
                    the evidence that is actually recorded (location, season, water, soil)
                    and marked “Preliminary” until the gaps are filled. Missing right now:{" "}
                    <span className="font-semibold">
                      {missingInputs.all.join(", ")}
                    </span>.
                  </p>
                  <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 font-semibold">
                    <Link to="/soil" className="underline-offset-2 hover:underline">
                      Add a soil test
                    </Link>
                    {selectedField && (
                      <Link
                        to={`/fields/${selectedField.id}/edit`}
                        className="underline-offset-2 hover:underline"
                      >
                        Update this field’s water availability
                      </Link>
                    )}
                  </div>
                  {missingInputs.optional.length > 0 && (
                    <p className="mt-2 text-xs text-amber-700">
                      Optional inputs that would sharpen the estimate:{" "}
                      {missingInputs.optional.join(", ")}.
                    </p>
                  )}
                </div>
              </div>
            </section>
          )}

          {batch.notes.length > 0 && (
            <div className="flex items-start gap-2 rounded-card border border-sky-200 bg-sky-50 p-4 text-sm text-sky-800">
              <Info className="mt-0.5 h-4 w-4 shrink-0" />
              <ul className="space-y-1">
                {batch.notes.map((note, index) => (
                  <li key={index}>• {note}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Results */}
          <section className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="mr-auto text-lg font-bold tracking-tight text-ink">Ranked suitability</h2>
              <StatusBadge tone="success" icon={<CheckCircle2 className="h-3.5 w-3.5" />} dot>
                {stats?.suitable ?? 0} potentially suitable
              </StatusBadge>
              <StatusBadge tone="warning" dot>
                {stats?.needs_information ?? 0} need more info
              </StatusBadge>
              <StatusBadge tone="danger" dot>
                {stats?.not_recommended ?? 0} not recommended
              </StatusBadge>
            </div>

            <div className="space-y-3">
              {batch.results.map((result, index) => (
                <CropResultCard
                  key={result.crop_id}
                  result={result}
                  rank={index + 1}
                  defaultExpanded={index === 0}
                  onCompare={(cropId) => openCompare([cropId])}
                />
              ))}
            </div>
          </section>

          <p className="text-center text-xs leading-relaxed text-ink-muted">{batch.disclaimer}</p>
        </>
      )}

      <HistoryPanel
        history={history}
        loading={loading}
        onRefresh={() => void reloadHistory()}
        onView={(batchId, label) => setDetail({ batchId, label })}
      />

      {selectedField && batch && (
        <>
          <CompareModal
            open={compareOpen}
            fieldId={selectedField.id}
            fieldName={selectedField.field_name}
            onClose={() => setCompareOpen(false)}
            candidates={batch.results}
            seed={compareSeed}
          />
          {detail && (
            <RecommendationDetailModal
              open
              fieldId={selectedField.id}
              batchId={detail.batchId}
              label={detail.label}
              onClose={() => setDetail(null)}
            />
          )}
        </>
      )}
    </div>
  );
}