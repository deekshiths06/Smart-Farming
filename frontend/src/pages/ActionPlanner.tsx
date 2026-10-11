import { useMemo } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  ClipboardList,
  Droplets,
  FlaskConical,
  MapPin,
  RefreshCw,
  Sprout,
} from "lucide-react";
import { PageHeader } from "../components/ui/PageHeader";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { Skeleton } from "../components/ui/Skeleton";
import { ActionCard } from "../components/actions/ActionCard";
import { useFields } from "../hooks/useFields";
import { useActions } from "../hooks/useActions";
import { cn } from "../lib/cn";
import { landStructure, SOIL_STATUS_LABELS, WATER_AVAILABILITY_LABELS } from "../lib/labels";
import {
  ACTION_GROUP_HINTS,
  ACTION_GROUP_LABELS,
  ACTION_GROUP_ORDER,
  type ActionGroup,
  type ActionRead,
} from "../types/action";

function formatDate(value?: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

function SummaryItem({
  icon,
  label,
  value,
  muted = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  muted?: boolean;
}) {
  return (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface-sunken text-brand-700">
        {icon}
      </span>
      <div className="min-w-0">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">{label}</p>
        <p className={cn("truncate text-sm font-medium", muted ? "text-ink-muted" : "text-ink")}>
          {value}
        </p>
      </div>
    </div>
  );
}

function GroupHeading({ group, count }: { group: ActionGroup; count: number }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-1">
      <h2 className="text-sm font-bold tracking-tight text-ink">
        {ACTION_GROUP_LABELS[group]}
        <span className="ml-2 font-normal text-ink-muted">({count})</span>
      </h2>
      <p className="text-xs text-ink-muted">{ACTION_GROUP_HINTS[group]}</p>
    </div>
  );
}

export default function ActionPlanner() {
  const { fields, loading: fieldsLoading, selectedField } = useFields();
  const { plan, loading, refreshing, busyId, error, reload, refresh, toggle } = useActions(
    selectedField?.id
  );

  const handleToggle = (action: ActionRead, completed: boolean) => {
    void toggle(action.id, completed);
  };

  const grouped = useMemo(() => {
    const pending = plan?.actions.filter((action) => !action.completed) ?? [];
    const result = {} as Record<ActionGroup, ActionRead[]>;
    for (const group of ACTION_GROUP_ORDER) {
      result[group] = pending.filter((action) => action.group_key === group);
    }
    return result;
  }, [plan]);

  const done = useMemo(
    () => plan?.actions.filter((action) => action.completed) ?? [],
    [plan]
  );

  const pendingCount = ACTION_GROUP_ORDER.reduce((total, group) => total + grouped[group].length, 0);

  const backLink = (
    <Link
      to="/crops"
      className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-700 transition-colors hover:text-brand-800"
    >
      <ArrowLeft className="h-4 w-4" />
      Back to Crop Recommendations
    </Link>
  );

  if (fieldsLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-20 rounded-panel" />
        <Skeleton className="h-28 rounded-panel" />
        <div className="space-y-3">
          {[...Array(3)].map((_, index) => (
            <Skeleton key={index} className="h-28 rounded-card" />
          ))}
        </div>
      </div>
    );
  }

  if (fields.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Your Farming Action Plan"
          description="Simple, step-by-step guidance built only from the information you have saved for your field."
          icon={<ClipboardList className="h-5 w-5" />}
        />
        <EmptyState
          icon={<Sprout className="h-8 w-8" />}
          title="Add a field to get your action plan"
          description="Your plan is built from a real field — its location, water, soil and the latest crop assessment. Create your first field to begin."
          action={
            <Link to="/fields/create">
              <Button rightIcon={<ArrowRight className="h-4 w-4" />}>Create your first field</Button>
            </Link>
          }
        />
      </div>
    );
  }

  const placeLabel = selectedField
    ? landStructure(selectedField as unknown as {
        locality?: string | null;
        sub_district?: string | null;
        district?: string | null;
        state?: string | null;
        country?: string | null;
      })
    : "Location confirmed";

  const waterLabel = selectedField?.water_availability
    ? WATER_AVAILABILITY_LABELS[selectedField.water_availability] ??
      selectedField.water_availability
    : "Not recorded yet";

  const soilLabel = selectedField
    ? SOIL_STATUS_LABELS[selectedField.soil_status] ?? "Not provided yet"
    : "Not provided yet";

  return (
    <div className="space-y-6">
      <div>{backLink}</div>

      <PageHeader
        title="Your Farming Action Plan"
        description="Simple, step-by-step guidance for your field, built only from the information you have saved. Open any step to see how to do it."
        icon={<ClipboardList className="h-5 w-5" />}
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => void refresh()}
            loading={refreshing}
            disabled={!selectedField || loading}
            leftIcon={<RefreshCw className="h-4 w-4" />}
          >
            Refresh plan
          </Button>
        }
      />

      {selectedField && (
        <section
          aria-label="Field summary"
          className="grid gap-4 rounded-panel border border-border bg-surface p-4 shadow-soft sm:grid-cols-2 lg:grid-cols-4"
        >
          <SummaryItem
            icon={<MapPin className="h-4 w-4" />}
            label="Field"
            value={selectedField.field_name}
          />
          <SummaryItem
            icon={<Sprout className="h-4 w-4" />}
            label="Crop"
            value={plan?.top_crop ?? "No crop chosen yet"}
            muted={!plan?.top_crop}
          />
          <SummaryItem
            icon={<CalendarDays className="h-4 w-4" />}
            label="Last assessment"
            value={
              plan?.has_assessment
                ? formatDate(plan.assessment_at) ?? "Completed"
                : "Not run yet"
            }
            muted={!plan?.has_assessment}
          />
          <SummaryItem
            icon={<Droplets className="h-4 w-4" />}
            label="Water available"
            value={waterLabel}
            muted={!selectedField.water_availability}
          />
          <SummaryItem
            icon={<FlaskConical className="h-4 w-4" />}
            label="Soil report"
            value={soilLabel}
            muted={selectedField.soil_status !== "available"}
          />
          <SummaryItem
            icon={<MapPin className="h-4 w-4" />}
            label="Location"
            value={placeLabel}
          />
        </section>
      )}

      {error && (
        <ErrorAlert
          title="Action plan unavailable"
          message={error}
          onRetry={() => void reload()}
        />
      )}

      {!plan?.has_assessment && plan && (
        <div className="rounded-panel border border-amber-200 bg-amber-50/60 p-4 text-sm leading-relaxed text-amber-900">
          No crop assessment has been run for this field yet, so weather and crop
          steps are not available. Run an assessment on the{" "}
          <Link to="/crops" className="font-semibold underline">
            Crop Recommendations
          </Link>{" "}
          page to unlock more of your plan.
        </div>
      )}

      {loading && !plan ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, index) => (
            <Skeleton key={index} className="h-28 rounded-card" />
          ))}
        </div>
      ) : plan && plan.actions.length === 0 ? (
        <EmptyState
          icon={<ClipboardList className="h-8 w-8" />}
          title="No actions needed right now"
          description="Everything ANNADATA can check is recorded and no weather risk has been raised. Add a soil test or run an assessment, then refresh the plan."
        />
      ) : plan ? (
        <>
          <p className="text-sm text-ink-soft">
            <span className="font-semibold text-ink">{pendingCount}</span> to do
            {done.length > 0 && (
              <>
                {" · "}
                <span className="font-semibold text-ink">{done.length}</span> done
              </>
            )}
          </p>

          {ACTION_GROUP_ORDER.map((group) =>
            grouped[group].length > 0 ? (
              <section key={group} className="space-y-3" aria-label={ACTION_GROUP_LABELS[group]}>
                <GroupHeading group={group} count={grouped[group].length} />
                {grouped[group].map((action) => (
                  <ActionCard
                    key={action.id}
                    action={action}
                    busy={busyId === action.id}
                    onToggle={handleToggle}
                  />
                ))}
              </section>
            ) : null
          )}

          {pendingCount === 0 && done.length > 0 && (
            <p className="rounded-panel border border-border bg-surface-muted p-4 text-sm text-ink-soft">
              You have finished every step ANNADATA can suggest for now. Well done.
            </p>
          )}

          {done.length > 0 && (
            <section className="space-y-3" aria-label="Completed">
              <h2 className="text-sm font-bold tracking-tight text-ink">
                Completed
                <span className="ml-2 font-normal text-ink-muted">({done.length})</span>
              </h2>
              {done.map((action) => (
                <ActionCard
                  key={action.id}
                  action={action}
                  busy={busyId === action.id}
                  onToggle={handleToggle}
                />
              ))}
            </section>
          )}

          <p className="text-xs leading-relaxed text-ink-muted">{plan.disclaimer}</p>
        </>
      ) : null}
    </div>
  );
}
