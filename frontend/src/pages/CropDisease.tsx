import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Camera,
  CheckCircle2,
  ImageUp,
  Info,
  Leaf,
  Microscope,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { StatusBadge } from "../components/ui/StatusBadge";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { EmptyState } from "../components/ui/EmptyState";
import { Skeleton } from "../components/ui/Skeleton";
import { Combobox, type ComboboxOption } from "../components/ui/Combobox";
import { useDiseaseIdentification } from "../hooks/useDisease";
import { diseaseErrorMessage } from "../services/disease";
import { catalogueApi } from "../services/catalogue";
import { cn } from "../lib/cn";
import type { CatalogueCrop } from "../types/catalogue";
import {
  DISEASE_STATUS_LABELS,
  DISEASE_STATUS_TONES,
  type DiseaseAssessment,
  type DiseaseCandidate,
} from "../types/disease";

type DiseaseState = ReturnType<typeof useDiseaseIdentification>;

const ACCEPTED = "image/jpeg,image/png,image/webp";

const UNSUPPORTED_MESSAGE =
  "This crop is in ANNADATA's crop catalogue, but the current AI disease model has not been trained or verified for it. Disease predictions are unavailable for this crop yet.";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  })}, ${date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}`;
}

function confidenceLabel(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}

function toOption(crop: CatalogueCrop): ComboboxOption {
  return {
    value: crop.key,
    label: crop.display_name,
    description: crop.category_label,
    badge: crop.model_supported ? "Disease AI" : undefined,
    data: crop,
  };
}

function resultSummary(assessment: DiseaseAssessment): { title: string; body: string } {
  switch (assessment.status) {
    case "healthy":
      return {
        title: "The leaf looks healthy",
        body: `The model did not find signs of the conditions it knows for ${assessment.crop_label}. Keep watching your crop and re-check if anything changes.`,
      };
    case "identified":
      return {
        title: `Possible ${assessment.predicted_disease_label}`,
        body: `The model's closest match for this ${assessment.crop_label} leaf is ${assessment.predicted_disease_label}. Treat this as a preliminary screening, not a confirmed diagnosis.`,
      };
    case "crop_mismatch":
      return {
        title: "Unable to identify reliably",
        body: `This photo did not look like a ${assessment.crop_label} leaf to the model (its closest match was ${assessment.predicted_crop_label} — ${assessment.predicted_disease_label}). Try a clear close-up of a single ${assessment.crop_label} leaf on a plain background.`,
      };
    case "low_confidence":
    default:
      return {
        title: "Unable to identify reliably",
        body: "The model was not confident enough about this photo. Use a sharp, well-lit close-up of one leaf, filling most of the frame against a plain background.",
      };
  }
}

function CandidateRow({ candidate }: { candidate: DiseaseCandidate }) {
  const width = Math.max(2, Math.round((candidate.confidence ?? 0) * 100));
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className="min-w-0 truncate font-medium text-ink">
          {candidate.disease_label}
          {candidate.crop_label ? (
            <span className="ml-1.5 font-normal text-ink-muted">({candidate.crop_label})</span>
          ) : null}
        </span>
        <span className="shrink-0 font-semibold text-ink-soft">
          {confidenceLabel(candidate.confidence)}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-sunken">
        <div
          className="h-full rounded-full bg-brand-500"
          style={{ width: `${width}%` }}
          aria-hidden="true"
        />
      </div>
    </div>
  );
}

function ResultPanel({
  assessment,
  onDismiss,
}: {
  assessment: DiseaseAssessment;
  onDismiss: () => void;
}) {
  const summary = resultSummary(assessment);
  const candidates = assessment.candidates ?? [];

  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <StatusBadge tone={DISEASE_STATUS_TONES[assessment.status]} dot>
          {DISEASE_STATUS_LABELS[assessment.status]}
        </StatusBadge>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss result"
          className="rounded-md p-1 text-ink-muted transition-colors hover:bg-surface-sunken hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div>
        <h2 className="text-lg font-bold tracking-tight text-ink">{summary.title}</h2>
        <p className="mt-1 text-sm leading-relaxed text-ink-soft">{summary.body}</p>
      </div>

      {assessment.confidence !== null && (
        <div className="flex items-center gap-3 text-sm">
          <span className="text-ink-muted">Model confidence</span>
          <span className="font-semibold text-ink">{confidenceLabel(assessment.confidence)}</span>
        </div>
      )}

      {candidates.length > 0 && (
        <div className="space-y-3 rounded-lg border border-border bg-surface-muted/60 p-3.5">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
            Closest matches from the model
          </p>
          {candidates.map((candidate) => (
            <CandidateRow key={candidate.class_name} candidate={candidate} />
          ))}
        </div>
      )}

      <div className="flex items-start gap-2.5 rounded-lg border border-amber-200 bg-amber-50/60 p-3 text-xs leading-relaxed text-amber-900">
        <Info className="mt-0.5 h-4 w-4 shrink-0" />
        <p>
          This is a screening result, not a diagnosis. Do not apply any chemical based on it alone
          — confirm with your local agricultural extension officer or plant protection expert
          first.
        </p>
      </div>

      <p className="text-[11px] leading-relaxed text-ink-muted">
        {assessment.model_name} · v{assessment.model_version} · photo processed on the server and
        not saved. {assessment.image_filename} ({formatBytes(assessment.image_size_bytes)}).
      </p>
    </Card>
  );
}

function UnsupportedCropNotice({ crop }: { crop: CatalogueCrop }) {
  return (
    <div
      role="note"
      className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50/70 p-3.5 text-sm leading-relaxed text-amber-900"
    >
      <Info className="mt-0.5 h-4 w-4 shrink-0" />
      <div>
        <p className="font-semibold">{crop.display_name} is in the catalogue, but not in the model</p>
        <p className="mt-1">{UNSUPPORTED_MESSAGE}</p>
      </div>
    </div>
  );
}

function UploadPanel({ state }: { state: DiseaseState }) {
  const { assessing, assess } = state;
  const [selected, setSelected] = useState<CatalogueCrop | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [symptoms, setSymptoms] = useState("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [latest, setLatest] = useState<DiseaseAssessment | null>(null);

  const cameraInputRef = useRef<HTMLInputElement>(null);
  const galleryInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!previewUrl) return;
    return () => URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const searchCrops = useCallback(async (query: string): Promise<ComboboxOption[]> => {
    const response = await catalogueApi.search({ q: query, limit: 100 });
    return response.items.map(toOption);
  }, []);

  const selectedOption = useMemo(
    () => (selected ? toOption(selected) : null),
    [selected]
  );

  // The model file must be present for *any* inference to run.
  const modelAvailable = state.crops.length > 0 && !state.cropsError;
  const selectedSupported = !!selected && selected.model_supported && modelAvailable;
  const modelCrop = selected
    ? state.crops.find((crop) => crop.key === selected.key) ?? null
    : null;

  const onlyHealthy = useMemo(
    () =>
      modelCrop !== null &&
      modelCrop.diseases.length > 0 &&
      modelCrop.diseases.every((disease) => disease.is_healthy),
    [modelCrop]
  );

  const chooseFile = (next: File | null) => {
    setFile(next);
    setPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return next ? URL.createObjectURL(next) : null;
    });
    setUploadError(null);
  };

  const handleInput = (event: React.ChangeEvent<HTMLInputElement>) => {
    const next = event.target.files?.[0] ?? null;
    event.target.value = "";
    if (next) chooseFile(next);
  };

  const canAnalyze = Boolean(selected && file) && selectedSupported && !assessing;

  const handleAnalyze = async () => {
    if (!selected || !file) return;
    setUploadError(null);
    try {
      const record = await assess(selected.key, file, symptoms);
      setLatest(record);
      chooseFile(null);
      setSymptoms("");
    } catch (err) {
      setUploadError(
        diseaseErrorMessage(err, "The photo could not be analysed right now. Please try again.")
      );
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card className="space-y-5">
        <Combobox
          id="disease-crop"
          label="Crop"
          value={selectedOption}
          onChange={(option) =>
            setSelected(option ? (option.data as CatalogueCrop) : null)
          }
          search={searchCrops}
          placeholder="Search crops by name…"
          searchHint="Search ANNADATA's full catalogue by any common or regional name — for example 'ragi', 'paddy', 'haldi', 'kela'."
          emptyMessage="No crops match that search. Try another name or a local name."
          errorMessage="The crop catalogue could not be loaded. Please try again."
        />

        {!selected && (
          <p className="text-xs leading-relaxed text-ink-muted">
            Pick the crop in your photo. The catalogue covers far more crops than the AI model, so
            we will tell you straight away whether the model can actually analyse your crop.
          </p>
        )}

        {selected && !selected.model_supported && <UnsupportedCropNotice crop={selected} />}

        {selected && selected.model_supported && !modelAvailable && (
          <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50/70 p-3.5 text-sm leading-relaxed text-amber-900">
            <Info className="mt-0.5 h-4 w-4 shrink-0" />
            <p>
              Disease identification is currently unavailable on the server, so no crop can be
              analysed right now. You can still browse the crop catalogue.
            </p>
          </div>
        )}

        {selectedSupported && modelCrop && (
          <>
            <details className="rounded-lg border border-border bg-surface-muted/50 p-3">
              <summary className="cursor-pointer text-sm font-medium text-ink-soft">
                Conditions the model can detect on {modelCrop.label}
              </summary>
              {onlyHealthy ? (
                <p className="mt-2 text-xs leading-relaxed text-ink-muted">
                  For this crop the model can only confirm a healthy-looking leaf — it does not
                  recognise specific diseases.
                </p>
              ) : (
                <ul className="mt-2 flex flex-wrap gap-1.5">
                  {modelCrop.diseases.map((disease) => (
                    <li
                      key={disease.class_name}
                      className={cn(
                        "rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset",
                        disease.is_healthy
                          ? "bg-emerald-50 text-emerald-700 ring-emerald-600/20"
                          : "bg-surface text-ink-soft ring-border-strong"
                      )}
                    >
                      {disease.disease_label}
                    </li>
                  ))}
                </ul>
              )}
            </details>

            <div>
              <span className="mb-1.5 block text-sm font-medium text-ink-soft">Leaf photo</span>
              {previewUrl ? (
                <div className="flex items-center gap-3 rounded-lg border border-border bg-surface p-2.5">
                  <img
                    src={previewUrl}
                    alt="Selected leaf"
                    className="h-16 w-16 rounded-md object-cover"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink">{file?.name}</p>
                    <p className="text-xs text-ink-muted">{file ? formatBytes(file.size) : ""}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => chooseFile(null)}
                    aria-label="Remove photo"
                    className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-surface-sunken hover:text-ink"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    leftIcon={<Camera className="h-4 w-4" />}
                    onClick={() => cameraInputRef.current?.click()}
                  >
                    Take photo
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    leftIcon={<ImageUp className="h-4 w-4" />}
                    onClick={() => galleryInputRef.current?.click()}
                  >
                    Choose image
                  </Button>
                </div>
              )}
              <input
                ref={cameraInputRef}
                type="file"
                accept={ACCEPTED}
                capture="environment"
                className="hidden"
                onChange={handleInput}
              />
              <input
                ref={galleryInputRef}
                type="file"
                accept={ACCEPTED}
                className="hidden"
                onChange={handleInput}
              />
              <p className="mt-1.5 text-xs leading-relaxed text-ink-muted">
                One leaf, filling most of the frame, on a plain background, in good light. JPEG,
                PNG or WebP, up to 5 MB. The photo is not stored.
              </p>
            </div>

            <div>
              <label
                htmlFor="disease-symptoms"
                className="mb-1.5 block text-sm font-medium text-ink-soft"
              >
                Anything you noticed (optional)
              </label>
              <textarea
                id="disease-symptoms"
                value={symptoms}
                onChange={(event) => setSymptoms(event.target.value)}
                rows={3}
                maxLength={2000}
                placeholder="e.g. yellow patches appeared after a week of rain"
                className="w-full rounded-lg border border-border-strong bg-surface px-3.5 py-2.5 text-sm text-ink shadow-soft transition-colors placeholder:text-ink-muted/70 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/20"
              />
            </div>

            {uploadError && <ErrorAlert title="Could not analyse the photo" message={uploadError} />}

            <Button
              fullWidth
              onClick={() => void handleAnalyze()}
              loading={assessing}
              disabled={!canAnalyze}
              leftIcon={<Sparkles className="h-4 w-4" />}
            >
              {assessing ? "Analysing…" : "Analyse photo"}
            </Button>
          </>
        )}
      </Card>

      <div>
        {latest ? (
          <ResultPanel assessment={latest} onDismiss={() => setLatest(null)} />
        ) : (
          <Card className="space-y-4">
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
              <Leaf className="h-5 w-5" />
            </span>
            <h2 className="text-base font-semibold text-ink">How this works</h2>
            <ol className="space-y-2.5 text-sm leading-relaxed text-ink-soft">
              <li className="flex gap-2.5">
                <span className="font-semibold text-brand-700">1.</span>
                Search the catalogue and choose the crop in your photo.
              </li>
              <li className="flex gap-2.5">
                <span className="font-semibold text-brand-700">2.</span>
                If the AI model supports that crop, add a clear close-up of a single leaf.
              </li>
              <li className="flex gap-2.5">
                <span className="font-semibold text-brand-700">3.</span>
                You get a preliminary screening. It never replaces a diagnosis by a local expert,
                and it gives no chemical advice.
              </li>
            </ol>
          </Card>
        )}
      </div>
    </div>
  );
}

function HistorySection({ state }: { state: DiseaseState }) {
  const { history, historyLoading, historyError, reloadHistory, remove } = state;
  const [removingId, setRemovingId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const handleRemove = async (id: number) => {
    setRemovingId(id);
    setActionError(null);
    try {
      await remove(id);
    } catch (err) {
      setActionError(diseaseErrorMessage(err, "That assessment could not be removed."));
    } finally {
      setRemovingId(null);
    }
  };

  if (historyLoading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((index) => (
          <Skeleton key={index} className="h-20 rounded-card" />
        ))}
      </div>
    );
  }

  if (historyError) {
    return (
      <ErrorAlert
        title="Past assessments unavailable"
        message={historyError}
        onRetry={() => void reloadHistory()}
      />
    );
  }

  if (history.length === 0) {
    return (
      <EmptyState
        icon={<Microscope className="h-8 w-8" />}
        title="No assessments yet"
        description="Your leaf screenings will appear here so you can look back at them over time."
      />
    );
  }

  return (
    <div className="space-y-3">
      {actionError && <ErrorAlert title="Something went wrong" message={actionError} />}
      {history.map((assessment) => (
        <Card key={assessment.id} className="flex flex-wrap items-center gap-3 py-3.5">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tone={DISEASE_STATUS_TONES[assessment.status]} dot>
                {DISEASE_STATUS_LABELS[assessment.status]}
              </StatusBadge>
              <span className="text-sm font-medium text-ink">{assessment.crop_label}</span>
              {assessment.predicted_disease_label && (
                <span className="truncate text-sm text-ink-soft">
                  · {assessment.predicted_disease_label}
                  {assessment.confidence !== null && (
                    <span className="text-ink-muted">
                      {" "}
                      ({confidenceLabel(assessment.confidence)})
                    </span>
                  )}
                </span>
              )}
            </div>
            <p className="mt-1 text-xs text-ink-muted">{formatDateTime(assessment.created_at)}</p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => void handleRemove(assessment.id)}
            loading={removingId === assessment.id}
            leftIcon={<Trash2 className="h-4 w-4" />}
          >
            Remove
          </Button>
        </Card>
      ))}
    </div>
  );
}

export default function CropDisease() {
  const state = useDiseaseIdentification();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Crop Disease Identification"
        description="Search any crop in ANNADATA's catalogue, then photograph a single leaf for a preliminary, model-based screening. This is a screening aid, not a diagnosis — no chemical advice is given."
        icon={<Microscope className="h-5 w-5" />}
      />

      <div className="flex items-start gap-3 rounded-panel border border-border bg-surface-muted p-4 text-sm leading-relaxed text-ink-soft">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-brand-700" />
        <p>
          ANNADATA's crop catalogue lists many crops, but the installed AI model was only trained
          and verified on a small set of them. Choose any crop from the catalogue — we will only
          run a prediction when the model actually supports it, and we will never invent a
          disease for a crop it does not know.
        </p>
      </div>

      <UploadPanel state={state} />

      <section className="space-y-3" aria-label="Past assessments">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-brand-700" />
          <h2 className="text-sm font-bold tracking-tight text-ink">Past assessments</h2>
        </div>
        <HistorySection state={state} />
      </section>
    </div>
  );
}
