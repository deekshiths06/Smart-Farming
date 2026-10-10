import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { ClipboardCheck, X } from "lucide-react";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { cn } from "../../lib/cn";
import { SOIL_PARAMETERS, SOIL_PARAMETER_METHOD_NOTE, TEXTURE_OPTIONS, formatSoilDate } from "../../lib/soil";
import { soilErrorMessage } from "../../services/soil";
import type {
  SoilMeasurement,
  SoilMeasurementPayload,
  SoilReport,
  SoilTexture,
  SourceKind,
} from "../../types/soil";

interface SoilMeasurementModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: SoilMeasurementPayload, measurementId?: number) => Promise<void>;
  initial?: SoilMeasurement | null;
  reports: SoilReport[];
}

type NumericForm = Record<string, string>;

const EMPTY_NUMERIC: NumericForm = Object.fromEntries(
  SOIL_PARAMETERS.map((meta) => [meta.key, ""])
);

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function numericFrom(measurement: SoilMeasurement | null | undefined): NumericForm {
  const form: NumericForm = { ...EMPTY_NUMERIC };
  if (!measurement) return form;
  for (const meta of SOIL_PARAMETERS) {
    const value = measurement[meta.key];
    form[meta.key] = value === null || value === undefined ? "" : String(value);
  }
  return form;
}

export function SoilMeasurementModal({
  open,
  onClose,
  onSubmit,
  initial,
  reports,
}: SoilMeasurementModalProps) {
  const isEdit = Boolean(initial);
  const [testedOn, setTestedOn] = useState(todayISO());
  const [testSource, setTestSource] = useState("");
  const [texture, setTexture] = useState<string>("");
  const [sourceKind, setSourceKind] = useState<SourceKind>("farmer_entered");
  const [reportId, setReportId] = useState<string>("");
  const [numeric, setNumeric] = useState<NumericForm>(EMPTY_NUMERIC);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    setTestedOn(initial?.tested_on ?? todayISO());
    setTestSource(initial?.test_source ?? "");
    setTexture(initial?.texture ?? "");
    setSourceKind(initial?.source_kind ?? "farmer_entered");
    setReportId(initial?.report_id ? String(initial.report_id) : "");
    setNumeric(numericFrom(initial));
    setError(null);
    setSubmitting(false);
  }, [open, initial]);

  const hasAnyValue = useMemo(
    () => Object.values(numeric).some((value) => value.trim() !== "") || texture !== "",
    [numeric, texture]
  );

  if (typeof document === "undefined") return null;

  const handleSubmit = async () => {
    setError(null);
    if (!testedOn) {
      setError("Record the date the soil was tested.");
      return;
    }
    if (testedOn > todayISO()) {
      setError("The soil test date cannot be in the future.");
      return;
    }
    if (!hasAnyValue) {
      setError("Enter at least one soil measurement before saving.");
      return;
    }
    if (sourceKind === "report_confirmed" && !reportId) {
      setError("Choose the uploaded report this reading was confirmed from.");
      return;
    }

    const payload: SoilMeasurementPayload = {
      tested_on: testedOn,
      test_source: testSource.trim() || null,
      source_kind: sourceKind,
      texture: (texture || null) as SoilTexture | null,
    };
    if (sourceKind === "report_confirmed") {
      payload.report_id = Number(reportId);
    }
    for (const meta of SOIL_PARAMETERS) {
      const raw = numeric[meta.key].trim();
      (payload as unknown as Record<string, number | null>)[meta.key] = raw === "" ? null : Number(raw);
    }

    setSubmitting(true);
    try {
      await onSubmit(payload, initial?.id);
      onClose();
    } catch (err) {
      setError(soilErrorMessage(err, "The soil measurement could not be saved. Please try again."));
      setSubmitting(false);
    }
  };

  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[1000] flex items-start justify-center overflow-y-auto p-4 sm:p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          <div
            className="fixed inset-0 bg-forest-950/45 backdrop-blur-[2px]"
            onClick={onClose}
            aria-hidden="true"
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={isEdit ? "Edit soil measurement" : "Add soil measurement"}
            initial={{ opacity: 0, scale: 0.97, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 8 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="relative my-4 w-full max-w-2xl rounded-panel border border-border bg-surface shadow-pop"
          >
            <div className="flex items-start justify-between gap-4 border-b border-border p-5 sm:p-6">
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
                  <ClipboardCheck className="h-5 w-5" />
                </span>
                <div>
                  <h2 className="text-lg font-bold tracking-tight text-ink">
                    {isEdit ? "Edit soil measurement" : "Add a soil measurement"}
                  </h2>
                  <p className="mt-0.5 text-sm text-ink-muted">
                    Enter only what your soil test reports. Every value is optional except the date
                    and at least one reading — nothing is estimated for you.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close"
                className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-surface-sunken"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="max-h-[65vh] space-y-5 overflow-y-auto p-5 sm:p-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  id="soil-tested-on"
                  type="date"
                  label="Date tested"
                  max={todayISO()}
                  value={testedOn}
                  onChange={(event) => setTestedOn(event.target.value)}
                  required
                />
                <Input
                  id="soil-test-source"
                  label="Tested by / source"
                  placeholder="e.g. KVK Hassan, Soil Health Card"
                  value={testSource}
                  onChange={(event) => setTestSource(event.target.value)}
                />
              </div>

              <fieldset className="space-y-3">
                <legend className="text-sm font-semibold text-ink">Measurements</legend>
                <div className="grid gap-4 sm:grid-cols-2">
                  {SOIL_PARAMETERS.map((meta) => (
                    <Input
                      key={meta.key}
                      id={`soil-${meta.key}`}
                      type="number"
                      inputMode="decimal"
                      label={meta.label}
                      hint={`${meta.unit ? `Enter in ${meta.unit} · ` : ""}${SOIL_PARAMETER_METHOD_NOTE[meta.key]}`}
                      placeholder={meta.placeholder}
                      min={meta.min}
                      max={meta.max}
                      step={meta.step}
                      value={numeric[meta.key]}
                      onChange={(event) =>
                        setNumeric((current) => ({ ...current, [meta.key]: event.target.value }))
                      }
                    />
                  ))}

                  <div className="w-full">
                    <label
                      htmlFor="soil-texture"
                      className="mb-1.5 block text-sm font-medium text-ink-soft"
                    >
                      Soil texture
                    </label>
                    <select
                      id="soil-texture"
                      value={texture}
                      onChange={(event) => setTexture(event.target.value)}
                      className={cn(
                        "h-11 w-full rounded-lg border border-border-strong bg-surface px-3.5 text-sm text-ink shadow-soft transition-colors",
                        "focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/20"
                      )}
                    >
                      <option value="">Not recorded</option>
                      {TEXTURE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <p className="mt-1.5 text-xs text-ink-muted">
                      Texture is judged by feel using the soil texture triangle and selects which
                      moisture reference band applies.
                    </p>
                  </div>
                </div>
              </fieldset>

              {reports.length > 0 && (
                <fieldset className="space-y-3 rounded-card border border-border bg-surface-muted p-4">
                  <legend className="px-1 text-sm font-semibold text-ink">Source of values</legend>
                  <div className="flex flex-wrap gap-2">
                    {(
                      [
                        { value: "farmer_entered", label: "Entered manually" },
                        { value: "report_confirmed", label: "Copied from an uploaded report" },
                      ] as const
                    ).map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => setSourceKind(option.value)}
                        className={cn(
                          "rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
                          sourceKind === option.value
                            ? "border-brand-600 bg-brand-50 text-brand-800"
                            : "border-border-strong bg-surface text-ink-soft hover:bg-surface-sunken"
                        )}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                  {sourceKind === "report_confirmed" && (
                    <div className="w-full">
                      <label
                        htmlFor="soil-report-link"
                        className="mb-1.5 block text-sm font-medium text-ink-soft"
                      >
                        Linked report
                      </label>
                      <select
                        id="soil-report-link"
                        value={reportId}
                        onChange={(event) => setReportId(event.target.value)}
                        className="h-11 w-full rounded-lg border border-border-strong bg-surface px-3.5 text-sm text-ink shadow-soft focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/20"
                      >
                        <option value="">Choose a report…</option>
                        {reports.map((report) => (
                          <option key={report.id} value={report.id}>
                            {report.original_filename}
                            {report.report_date ? ` · ${formatSoilDate(report.report_date)}` : ""}
                          </option>
                        ))}
                      </select>
                      <p className="mt-1.5 text-xs text-ink-muted">
                        Values are still typed in by you — ANNADATA does not read the file
                        automatically.
                      </p>
                    </div>
                  )}
                </fieldset>
              )}

              {error && (
                <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
                  {error}
                </p>
              )}
            </div>

            <div className="flex justify-end gap-2 border-t border-border p-5 sm:p-6">
              <Button variant="outline" onClick={onClose} disabled={submitting}>
                Cancel
              </Button>
              <Button onClick={() => void handleSubmit()} loading={submitting}>
                {isEdit ? "Save changes" : "Save measurement"}
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  );
}
