import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  CalendarDays,
  History,
  MapPin,
  Scale,
  Search,
  Sparkles,
  Sprout,
  Wheat,
  Zap,
} from "lucide-react";
import { PageHeader } from "../components/ui/PageHeader";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { Input } from "../components/ui/Input";
import { Skeleton } from "../components/ui/Skeleton";
import { CropResultCard } from "../components/crops/CropResultCard";
import { CropDetailModal } from "../components/crops/CropDetailModal";
import { CompareModal } from "../components/crops/CompareModal";
import { PastAssessments } from "../components/crops/HistoryPanel";
import { RecommendationDetailModal } from "../components/crops/RecommendationDetailModal";
import type { CropEvaluation } from "../types/crop";
import { useFields } from "../hooks/useFields";
import { useCrops } from "../hooks/useCrops";
import { cropsErrorMessage } from "../services/crops";
import { landStructure } from "../lib/labels";
import { formatSoilDate } from "../lib/soil";
import {
  CROP_CATEGORY_LABELS,
  MATCH_CATEGORY_HINTS,
  MATCH_CATEGORY_LABELS,
  MATCH_CATEGORY_ORDER,
  cropSeasons,
  matchCategoryOf,
  seasonLabel,
} from "../lib/crops";
import { cn } from "../lib/cn";

// Forecast-derived inputs come from the field's coordinates, not from the
// farmer, so they are never listed as "not yet recorded" gaps.
const WEATHER_FACTORS = new Set(["temperature", "rainfall"]);

// How many crops to show per category before the farmer asks for more. This is
// a display aid, not a cap on what the engine evaluates or returns.
const GROUP_LIMIT = 6;

export default function CropRecommendations() {
  const { fields, loading: fieldsLoading, selectedField } = useFields();

  // A signature of the field's own inputs. When it changes (e.g. the farmer
  // edits the location or water), the hook clears stale results and recalculates.
  const fieldRevision = selectedField
    ? [
        selectedField.id,
        selectedField.updated_at,
        selectedField.latitude,
        selectedField.longitude,
        selectedField.state,
        selectedField.water_availability,
        selectedField.water_source,
      ].join("|")
    : null;

  const {
    batch,
    history,
    loading,
    generating,
    error,
    generate,
    reloadHistory,
  } = useCrops(selectedField?.id, fieldRevision);

  const [compareOpen, setCompareOpen] = useState(false);
  const [compareSeed, setCompareSeed] = useState<number[]>([]);
  const [runError, setRunError] = useState<string | null>(null);
  const [detail, setDetail] = useState<{ batchId: string; label: string } | null>(null);
  const [detailCrop, setDetailCrop] = useState<CropEvaluation | null>(null);
  const [activeTab, setActiveTab] = useState<"new" | "past">("new");

  // Discovery controls for the full catalogue: search by name, narrow by the
  // crop's own category and by the season it documents. Everything already came
  // back from the engine; this only helps the farmer find it.
  const [query, setQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [seasonFilter, setSeasonFilter] = useState("all");
  const [showAllGroups, setShowAllGroups] = useState<Record<string, boolean>>({});

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

  // Inputs the engine could not check for at least one crop. Derived from the
  // payload so the wording always matches what the engine actually reported.
  const missingInputs = useMemo(() => {
    if (!batch) return null;
    const essential = new Map<string, string>();
    const optional = new Set<string>();
    for (const result of batch.results) {
      for (const factor of Object.values(result.factors ?? {})) {
        if (factor.status !== "missing_input") continue;
        if (WEATHER_FACTORS.has(factor.factor)) continue;
        if (factor.is_essential) essential.set(factor.factor, factor.label);
        else optional.add(factor.label);
      }
    }
    const all = [...essential.values(), ...optional.values()];
    return { essential: [...essential.values()], optional: [...optional.values()], all };
  }, [batch]);

  // "Highly Recommended" is exactly the engine's "Good match" category: suitable
  // with every scored factor evaluated. There is no arbitrary cap — every crop
  // that genuinely clears the bar is shown.
  const highlyRecommended = useMemo(() => {
    if (!batch) return [];
    return batch.results
      .filter((result) => matchCategoryOf(result) === "good_match")
      .sort(
        (a, b) =>
          (b.score ?? 0) - (a.score ?? 0) || a.display_name.localeCompare(b.display_name)
      );
  }, [batch]);

  // When nothing clears the bar, name the strongest possible options and the
  // inputs that would firm them up — never push a preliminary crop as confirmed.
  const nearMiss = useMemo(() => {
    if (!batch) return null;
    const candidates = batch.results
      .filter((result) => result.status === "suitable")
      .sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
    if (candidates.length === 0) return null;
    const needed = new Set<string>();
    for (const result of candidates) {
      for (const label of result.missing ?? []) needed.add(label);
      for (const factor of batch.config.essential_factors ?? []) {
        const evaluated = result.factors?.[factor];
        if (evaluated && evaluated.status === "missing_input") needed.add(evaluated.label);
      }
    }
    return {
      names: candidates.slice(0, 3).map((result) => result.display_name),
      needed: [...needed],
    };
  }, [batch]);

  const cropCategories = useMemo(() => {
    if (!batch) return [];
    return [...new Set(batch.results.map((result) => result.category))].sort();
  }, [batch]);

  const filteredResults = useMemo(() => {
    if (!batch) return [];
    const q = query.trim().toLowerCase();
    return batch.results.filter((result) => {
      if (
        q &&
        !result.display_name.toLowerCase().includes(q) &&
        !result.crop_name.toLowerCase().includes(q)
      ) {
        return false;
      }
      if (categoryFilter !== "all" && result.category !== categoryFilter) return false;
      if (seasonFilter !== "all" && !cropSeasons(result).includes(seasonFilter)) return false;
      return true;
    });
  }, [batch, query, categoryFilter, seasonFilter]);

  const resultGroups = useMemo(() => {
    return MATCH_CATEGORY_ORDER.map((category) => ({
      category,
      items: filteredResults.filter((result) => matchCategoryOf(result) === category),
    })).filter((group) => group.items.length > 0);
  }, [filteredResults]);

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

  const soilLine = !batch?.soil.has_measurement
    ? "no soil test recorded"
    : batch.soil.is_stale || batch.soil.is_future
      ? "soil test on file, not used for scoring"
      : `soil test from ${formatSoilDate(batch.soil.tested_on)}`;

  const placeLabel = landStructure(
    selectedField as unknown as {
      locality?: string | null;
      sub_district?: string | null;
      district?: string | null;
      state?: string | null;
      country?: string | null;
    }
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Crop Recommendations"
        description={
          activeTab === "new"
            ? "Every crop is scored against your field's recorded soil, water and season, plus the live temperature and rainfall forecast for its location. Forecast risks are shown as context."
            : "Reopen any assessment saved for this field. Each run keeps its original inputs and recommendations, so nothing has to be recomputed."
        }
        icon={<Wheat className="h-5 w-5" />}
        actions={
          activeTab === "new" ? (
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
          ) : undefined
        }
      />

      <div>
        <Link
          to="/actions"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-700 transition-colors hover:text-brand-800"
        >
          View Action Planner
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      <div
        role="tablist"
        aria-label="Crop recommendation sections"
        className="inline-flex items-center gap-0.5 rounded-lg border border-border bg-surface-muted p-0.5 shadow-soft"
      >
        {(
          [
            { value: "new", label: "New Assessment", icon: Zap },
            { value: "past", label: "Past Assessments", icon: History },
          ] as const
        ).map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.value;
          return (
            <button
              key={tab.value}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setActiveTab(tab.value)}
              className={cn(
                "inline-flex items-center gap-2 rounded-md px-3.5 py-2 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600",
                active
                  ? "bg-brand-600 text-white shadow-soft"
                  : "text-ink-soft hover:bg-surface-sunken hover:text-ink"
              )}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-ink-muted">
        <MapPin className="h-4 w-4 shrink-0 text-ink-muted" />
        <span className="font-medium text-ink-soft">{selectedField?.field_name}</span>
        {placeLabel ? <span>· {placeLabel}</span> : null}
        {selectedField?.latitude != null && selectedField?.longitude != null ? (
          <span>
            · {selectedField.latitude.toFixed(3)}, {selectedField.longitude.toFixed(3)}
          </span>
        ) : null}
      </p>

      {activeTab === "new" && (error || runError) && (
        <ErrorAlert
          title="Recommendations could not be loaded"
          message={runError ?? error ?? ""}
          onRetry={() => void handleRun()}
        />
      )}

      {activeTab === "past" ? (
        <PastAssessments
          history={history}
          loading={loading}
          fieldName={selectedField?.field_name}
          location={placeLabel}
          onView={(batchId, label) => setDetail({ batchId, label })}
          onRefresh={() => void reloadHistory()}
        />
      ) : (
        <>
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
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-card border border-border bg-surface px-4 py-3 text-sm text-ink-soft">
            <span className="inline-flex items-center gap-1.5">
              <CalendarDays className="h-4 w-4 text-ink-muted" />
              Assessed {new Date(batch.generated_at).toLocaleString()}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <MapPin className="h-4 w-4 text-ink-muted" />
              {selectedField?.field_name}
              {placeLabel ? ` · ${placeLabel}` : ""}
            </span>
            <span>{seasonLabel(batch.season)} season</span>
            <span>{soilLine}</span>
            <span>
              {batch.weather.available
                ? `live ${batch.weather.source} temperature & rainfall forecast scored for this location`
                : `live weather not scored — ${batch.weather.reason ?? "unavailable for this location"}`}
            </span>
          </div>

          {missingInputs && missingInputs.all.length > 0 && (
            <div className="flex items-start gap-2 rounded-card border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <p>
                Scored as preliminary estimates — not yet recorded:{" "}
                <span className="font-semibold">{missingInputs.all.join(", ")}</span>.{" "}
                <Link to="/soil" className="font-semibold underline-offset-2 hover:underline">
                  Add a soil test
                </Link>
                {selectedField && (
                  <>
                    {" · "}
                    <Link
                      to={`/fields/${selectedField.id}/edit`}
                      className="font-semibold underline-offset-2 hover:underline"
                    >
                      Update water availability
                    </Link>
                  </>
                )}
              </p>
            </div>
          )}

          <section className="space-y-4 rounded-panel border border-brand-200 bg-brand-50/60 p-4 sm:p-5">
            <div className="flex items-start gap-2">
              <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />
              <div>
                <h2 className="text-lg font-bold tracking-tight text-ink">
                  Highly Recommended for Your Field
                </h2>
                <p className="text-sm text-ink-muted">
                  Crops that clear the confidence bar for {selectedField?.field_name}.
                </p>
              </div>
            </div>

            {highlyRecommended.length > 0 ? (
              <>
                <p className="text-sm text-ink-soft">
                  {highlyRecommended.length} crop{highlyRecommended.length === 1 ? "" : "s"}{" "}
                  clear the confidence bar on the recorded soil, water and season, and the live
                  forecast for this location — with every scored factor evaluated.
                </p>
                <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
                  {highlyRecommended.map((result) => (
                    <CropResultCard
                      key={result.crop_id}
                      result={result}
                      onViewDetails={setDetailCrop}
                    />
                  ))}
                </div>
              </>
            ) : nearMiss ? (
              <p className="text-sm text-ink-soft">
                No crop clears the confidence bar yet. The strongest candidates so far —{" "}
                <span className="font-semibold">{nearMiss.names.join(", ")}</span> — are still
                possible options
                {nearMiss.needed.length > 0 ? (
                  <>: record {nearMiss.needed.join(", ")} to firm them up</>
                ) : null}
                . They remain in the grouped list below.
              </p>
            ) : (
              <p className="text-sm text-ink-soft">
                No crop currently meets the strong-suitability criteria for this field. Review
                the grouped list below and the recorded inputs.
              </p>
            )}
          </section>

          <section className="space-y-4">
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <h2 className="text-lg font-bold tracking-tight text-ink">
                Every crop, grouped by fit
              </h2>
              <p className="text-sm text-ink-muted">
                {filteredResults.length} of {batch.results.length} shown ·{" "}
                {stats?.suitable ?? 0} potentially suitable · {stats?.needs_information ?? 0} need
                more info · {stats?.not_recommended ?? 0} not recommended
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr]">
              <Input
                id="crop-search"
                type="search"
                placeholder="Search crops by name"
                aria-label="Search crops by name"
                value={query}
                leadingIcon={<Search className="h-4 w-4" />}
                onChange={(event) => setQuery(event.target.value)}
              />
              <select
                aria-label="Filter by crop category"
                value={categoryFilter}
                onChange={(event) => setCategoryFilter(event.target.value)}
                className="h-11 w-full rounded-lg border border-border-strong bg-surface px-3.5 text-sm text-ink shadow-soft focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/20"
              >
                <option value="all">All crop categories</option>
                {cropCategories.map((category) => (
                  <option key={category} value={category}>
                    {CROP_CATEGORY_LABELS[category] ?? category}
                  </option>
                ))}
              </select>
              <select
                aria-label="Filter by season"
                value={seasonFilter}
                onChange={(event) => setSeasonFilter(event.target.value)}
                className="h-11 w-full rounded-lg border border-border-strong bg-surface px-3.5 text-sm text-ink shadow-soft focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/20"
              >
                <option value="all">All seasons</option>
                <option value="kharif">Kharif (monsoon)</option>
                <option value="rabi">Rabi (winter)</option>
                <option value="zaid">Zaid (summer)</option>
              </select>
            </div>

            {resultGroups.length === 0 ? (
              <p className="rounded-card border border-border bg-surface px-4 py-6 text-center text-sm text-ink-muted">
                No crops match your search or filters. Try clearing them.
              </p>
            ) : (
              resultGroups.map((group) => {
                const expanded = showAllGroups[group.category];
                const shown = expanded ? group.items : group.items.slice(0, GROUP_LIMIT);
                return (
                  <div key={group.category} className="space-y-3">
                    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-t border-border pt-4">
                      <h3 className="text-base font-bold tracking-tight text-ink">
                        {MATCH_CATEGORY_LABELS[group.category]}
                      </h3>
                      <span className="text-sm text-ink-muted">({group.items.length})</span>
                    </div>
                    <p className="text-sm text-ink-muted">
                      {MATCH_CATEGORY_HINTS[group.category]}
                    </p>
                    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
                      {shown.map((result) => (
                        <CropResultCard
                          key={result.crop_id}
                          result={result}
                          onViewDetails={setDetailCrop}
                        />
                      ))}
                    </div>
                    {group.items.length > shown.length && (
                      <Button
                        variant="outline"
                        onClick={() =>
                          setShowAllGroups((current) => ({
                            ...current,
                            [group.category]: true,
                          }))
                        }
                      >
                        Show all {group.items.length} in {MATCH_CATEGORY_LABELS[group.category]}
                      </Button>
                    )}
                  </div>
                );
              })
            )}
          </section>

          <p className="text-center text-xs leading-relaxed text-ink-muted">{batch.disclaimer}</p>
        </>
      )}
        </>
      )}

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
          <CropDetailModal
            open={detailCrop !== null}
            crop={detailCrop}
            config={batch.config}
            soil={batch.soil}
            weather={batch.weather}
            onClose={() => setDetailCrop(null)}
          />
        </>
      )}

      {selectedField && detail && (
        <RecommendationDetailModal
          open
          fieldId={selectedField.id}
          batchId={detail.batchId}
          label={detail.label}
          onClose={() => setDetail(null)}
        />
      )}
    </div>
  );
}
