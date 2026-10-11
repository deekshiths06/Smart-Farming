import { ArrowRight } from "lucide-react";
import { CropImage } from "./CropImage";
import { Button } from "../ui/Button";
import { StatusBadge } from "../ui/StatusBadge";
import {
  CROP_STATUS_TONE,
  MATCH_CATEGORY_LABELS,
  MATCH_CATEGORY_TONE,
  formatScore,
  matchCategoryOf,
} from "../../lib/crops";
import type { CropEvaluation } from "../../types/crop";

/** A single, honest line drawn from the engine's own verdict — never invented. */
function summaryFor(result: CropEvaluation): string {
  const missing = Object.values(result.factors ?? {})
    .filter((factor) => factor.status === "missing_input" && factor.is_essential)
    .map((factor) => factor.label);

  if (result.status === "needs_information") {
    return missing.length > 0
      ? `Needs ${missing.join(", ")} to decide.`
      : "Needs more field information to decide.";
  }

  const hasScore =
    result.score !== null && result.score !== undefined && !Number.isNaN(result.score);
  const score = hasScore ? ` (${formatScore(result.score)})` : "";

  if (result.status === "not_recommended") {
    return "Recorded requirements are not met right now.";
  }
  return result.preliminary
    ? `Matches recorded requirements${score}; preliminary estimate.`
    : `Matches recorded requirements${score}.`;
}

export function CropResultCard({
  result,
  onViewDetails,
}: {
  result: CropEvaluation;
  onViewDetails?: (crop: CropEvaluation) => void;
}) {
  const tone = CROP_STATUS_TONE[result.status] ?? "neutral";
  const summary = summaryFor(result);
  const category = matchCategoryOf(result);

  return (
    <article className="flex h-full flex-col overflow-hidden rounded-panel border border-border bg-surface shadow-card transition-shadow hover:shadow-pop">
      <CropImage
        cropName={result.crop_name}
        displayName={result.display_name}
        className="h-40 w-full object-cover"
        wrapperClassName="h-40 w-full"
      />
      <div className="flex flex-1 flex-col gap-2.5 p-4">
        <h3 className="font-display text-base font-bold tracking-tight text-ink">
          {result.display_name}
        </h3>
        <div className="flex flex-wrap items-center gap-1.5">
          <StatusBadge tone={MATCH_CATEGORY_TONE[category]} dot className="self-start">
            {MATCH_CATEGORY_LABELS[category]}
          </StatusBadge>
          <StatusBadge tone={tone} className="self-start">
            {result.status_label}
          </StatusBadge>
        </div>
        <p className="line-clamp-1 min-h-[1.25rem] text-sm text-ink-muted" title={summary}>
          {summary}
        </p>
        <Button
          fullWidth
          className="mt-auto"
          onClick={() => onViewDetails?.(result)}
          disabled={!onViewDetails}
          rightIcon={<ArrowRight className="h-4 w-4" />}
        >
          View Details
        </Button>
      </div>
    </article>
  );
}
