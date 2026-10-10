import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  CheckCircle2,
  FlaskConical,
  MapPin,
  Plus,
  RefreshCw,
  Sprout,
} from "lucide-react";
import { PageHeader } from "../components/ui/PageHeader";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { Skeleton } from "../components/ui/Skeleton";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { ImageWithFallback } from "../components/ui/ImageWithFallback";
import { SoilParameterCard } from "../components/soil/SoilParameterCard";
import { SoilMeasurementModal } from "../components/soil/SoilMeasurementModal";
import { SoilHistoryPanel } from "../components/soil/SoilHistoryPanel";
import { SoilReportsPanel } from "../components/soil/SoilReportsPanel";
import { useFields } from "../hooks/useFields";
import { useSoil } from "../hooks/useSoil";
import { soilApi } from "../services/soil";
import { SOIL_PARAMETER_LABELS, SOIL_PARAMETER_METHOD, SOIL_PARAMETER_WHY, formatSoilDate } from "../lib/soil";
import { landStructure } from "../lib/labels";
import type { SoilMeasurement, SoilParameterKey } from "../types/soil";

const CARD_ORDER: SoilParameterKey[] = [
  "ph",
  "nitrogen",
  "phosphorus",
  "potassium",
  "ec",
  "organic_carbon",
  "moisture",
  "texture",
];

export default function SoilIntelligence() {
  const { fields, loading: fieldsLoading, selectedField } = useFields();
  const {
    data,
    loading,
    error,
    reload,
    createMeasurement,
    updateMeasurement,
    deleteMeasurement,
    uploadReport,
  } = useSoil(selectedField?.id);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<SoilMeasurement | null>(null);
  const [pendingDelete, setPendingDelete] = useState<SoilMeasurement | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const noticeTimer = useRef<number | null>(null);

  const showNotice = (message: string) => {
    if (noticeTimer.current !== null) window.clearTimeout(noticeTimer.current);
    setNotice(message);
    noticeTimer.current = window.setTimeout(() => setNotice(null), 5000);
  };

  useEffect(() => {
    return () => {
      if (noticeTimer.current !== null) window.clearTimeout(noticeTimer.current);
    };
  }, []);

  if (fieldsLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-20 rounded-panel" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, index) => (
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
          title="Soil Intelligence"
          description="Record soil test values for a field and see how they compare to documented agronomic ranges."
          icon={<FlaskConical className="h-5 w-5" />}
        />
        <EmptyState
          icon={<FlaskConical className="h-8 w-8" />}
          title="Add a field to record its soil"
          description="Soil readings belong to a real field. Create your first field so ANNADATA can keep its soil history and compare each value to a verifiable reference range."
          action={
            <Link to="/fields/create">
              <Button rightIcon={<Sprout className="h-4 w-4" />}>Create your first field</Button>
            </Link>
          }
        />
      </div>
    );
  }

  const openAdd = () => {
    setEditing(null);
    setModalOpen(true);
  };

  const openEdit = (measurement: SoilMeasurement) => {
    setEditing(measurement);
    setModalOpen(true);
  };

  const handleSubmit = async (payload: Parameters<typeof createMeasurement>[0], measurementId?: number) => {
    if (measurementId) {
      await updateMeasurement(measurementId, payload);
      showNotice("Soil measurement updated.");
    } else {
      await createMeasurement(payload);
      showNotice("Soil measurement recorded.");
    }
  };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await deleteMeasurement(pendingDelete.id);
      showNotice("Soil measurement deleted.");
      setPendingDelete(null);
    } finally {
      setDeleting(false);
    }
  };

  const completeness = data?.completeness;
  const missing = (completeness?.missing ?? CARD_ORDER) as SoilParameterKey[];
  const percent = completeness?.percent ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Soil Intelligence"
        description="Record soil test values for a field and see how they compare to documented agronomic ranges."
        icon={<FlaskConical className="h-5 w-5" />}
        actions={
          <>
            <Button
              variant="outline"
              onClick={() => void reload()}
              leftIcon={<RefreshCw className="h-4 w-4" />}
            >
              Refresh
            </Button>
            <Button onClick={openAdd} leftIcon={<Plus className="h-4 w-4" />}>
              Add measurement
            </Button>
          </>
        }
      />

      <section className="relative isolate overflow-hidden rounded-panel shadow-soft">
        <ImageWithFallback
          src="/assets/crop-field.jpg"
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="hero-gradient-left absolute inset-0" aria-hidden="true" />
        <div className="leaf-pattern absolute inset-0 opacity-30" />
        <div className="relative px-6 py-6 sm:px-8">
          <p className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-widest text-brand-300">
            <MapPin className="h-3.5 w-3.5" />
            {selectedField?.field_name}
          </p>
          <p className="font-display mt-1 text-lg font-bold tracking-tight text-white">
            {landStructure(
              selectedField as unknown as {
                locality?: string | null;
                sub_district?: string | null;
                district?: string | null;
                state?: string | null;
                country?: string | null;
              }
            )}
          </p>
          <p className="mt-1 text-xs text-white/70">
            Readings are compared to documented reference ranges. Change field from the top bar.
          </p>
        </div>
      </section>

      {error && (
        <ErrorAlert title="Soil record could not be loaded" message={error} onRetry={() => void reload()} />
      )}

      {notice && (
        <div
          role="status"
          className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800"
        >
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          {notice}
        </div>
      )}

      {loading && !data ? (
        <div className="space-y-6">
          <Skeleton className="h-24 rounded-panel" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[...Array(6)].map((_, index) => (
              <Skeleton key={index} className="h-40 rounded-card" />
            ))}
          </div>
        </div>
      ) : !data ? null : (
        <>
          {/* Completeness + summary */}
          <section className="rounded-panel border border-border bg-surface p-5 shadow-card sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <span
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
                    data.has_measurements ? "bg-brand-50 text-brand-700" : "bg-surface-sunken text-ink-muted"
                  }`}
                >
                  {data.has_measurements ? (
                    <CheckCircle2 className="h-5 w-5" />
                  ) : (
                    <AlertCircle className="h-5 w-5" />
                  )}
                </span>
                <div>
                  <h2 className="font-display text-base font-bold tracking-tight text-ink">
                    {data.has_measurements
                      ? `Latest test: ${formatSoilDate(data.last_tested_on)}`
                      : "No soil measurements recorded yet"}
                  </h2>
                  <p className="mt-0.5 text-sm text-ink-muted">
                    {data.has_measurements
                      ? data.last_tested_source
                        ? `Tested by ${data.last_tested_source}.`
                        : "Readings are compared against documented reference ranges below."
                      : "Add the values from your soil test. Every parameter is optional — enter what you have."}
                  </p>
                </div>
              </div>
              {!data.has_measurements && (
                <Button onClick={openAdd} leftIcon={<Plus className="h-4 w-4" />}>
                  Add first measurement
                </Button>
              )}
            </div>

            <div className="mt-5">
              <div className="flex items-center justify-between text-xs font-medium text-ink-muted">
                <span>Measurement completeness</span>
                <span>
                  {completeness?.measured_count ?? 0} of {completeness?.total_count ?? 8} recorded
                </span>
              </div>
              <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-surface-sunken">
                <div
                  className="h-full rounded-full bg-brand-600 transition-[width] duration-300"
                  style={{ width: `${percent}%` }}
                />
              </div>
            </div>
          </section>

          {/* Assessment cards */}
          <section className="space-y-4">
            <div>
              <h2 className="font-display text-lg font-extrabold tracking-tight text-ink">Assessment</h2>
              <p className="text-xs text-ink-muted">
                Each value is compared to the most specific applicable reference range — soil class,
                then region, then general guidance.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {CARD_ORDER.map((key) => (
                <SoilParameterCard key={key} assessment={data.assessment[key]} />
              ))}
            </div>
          </section>

          {/* Missing measurements */}
          {missing.length > 0 && (
            <section className="space-y-3 rounded-panel border border-border bg-surface p-5 shadow-card sm:p-6">
              <div>
                <h2 className="text-base font-semibold text-ink">
                  Optional measurements you haven't recorded ({missing.length})
                </h2>
                <p className="mt-0.5 text-xs text-ink-muted">
                  Leaving these blank is completely fine — they will sharpen the picture when you
                  have them.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {missing.map((key) => (
                  <div
                    key={key}
                    className="rounded-card border border-dashed border-border-strong bg-surface-muted p-3"
                  >
                    <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-ink">
                      {SOIL_PARAMETER_LABELS[key]}
                      {SOIL_PARAMETER_METHOD[key]?.tone === "lab" && (
                        <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-700">
                          Lab test
                        </span>
                      )}
                    </p>
                    <p className="mt-1 text-xs leading-relaxed text-ink-muted">
                      {SOIL_PARAMETER_WHY[key]}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}

          <SoilHistoryPanel
            history={data.history}
            onAdd={openAdd}
            onEdit={openEdit}
            onDelete={(measurement) => setPendingDelete(measurement)}
          />

          <SoilReportsPanel
            reports={data.reports}
            onUpload={uploadReport}
            onDownload={(report) => soilApi.downloadReport(selectedField!.id, report)}
          />

          <p className="text-center text-xs leading-relaxed text-ink-muted">
            ANNADATA stores only the values you enter and compares them to documented, cited
            reference ranges. It never estimates a missing value, and an out-of-range reading is a
            signal to investigate — not a diagnosis.
          </p>
        </>
      )}

      <SoilMeasurementModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleSubmit}
        initial={editing}
        reports={data?.reports ?? []}
      />

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete this soil measurement?"
        description="This removes the test event and its values from the field's history. This cannot be undone."
        confirmLabel="Delete measurement"
        loading={deleting}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}
