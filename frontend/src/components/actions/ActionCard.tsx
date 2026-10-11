import { useState, type ReactNode } from "react";
import {
  Ban,
  Check,
  CheckCircle2,
  ChevronDown,
  Clock,
  Eye,
  Info,
  ListOrdered,
  Package,
} from "lucide-react";
import { StatusBadge, type BadgeTone } from "../ui/StatusBadge";
import { cn } from "../../lib/cn";
import type { ActionRead } from "../../types/action";

const CATEGORY_LABELS: Record<string, string> = {
  information: "Field information",
  soil: "Soil",
  water: "Water",
  weather: "Weather",
  crop: "Crop",
};

const PRIORITY_LABELS: Record<string, string> = {
  high: "High priority",
  medium: "Medium priority",
  low: "Low priority",
};

/**
 * Only genuine forecast risks get a strong (warning/danger) treatment. Routine
 * information-gathering and review steps stay calm so they never read as alarms.
 */
function toneFor(action: ActionRead): BadgeTone {
  const isRisk = action.category === "weather";
  if (isRisk && action.priority === "high") return "danger";
  if (isRisk && action.priority === "medium") return "warning";
  if (action.priority) return "brand";
  return "neutral";
}

function containerClass(action: ActionRead): string {
  if (action.completed) return "border-border bg-surface-muted";
  if (action.category === "weather" && action.priority === "high") {
    return "border-red-200 bg-red-50/60";
  }
  if (action.category === "weather" && action.priority === "medium") {
    return "border-amber-200 bg-amber-50/50";
  }
  return "border-border bg-surface";
}

function DetailSection({
  icon,
  title,
  children,
  tone = "default",
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
  tone?: "default" | "warning" | "avoid" | "done";
}) {
  const toneClass =
    tone === "warning"
      ? "text-amber-700"
      : tone === "avoid"
        ? "text-red-600"
        : tone === "done"
          ? "text-emerald-700"
          : "text-ink-soft";
  return (
    <div>
      <p className={cn("flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide", toneClass)}>
        {icon}
        {title}
      </p>
      <div className="mt-1.5 text-sm leading-relaxed text-ink-soft">{children}</div>
    </div>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="list-disc space-y-1 pl-5 marker:text-ink-muted/60">
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </ul>
  );
}

export function ActionCard({
  action,
  busy = false,
  onToggle,
}: {
  action: ActionRead;
  busy?: boolean;
  onToggle: (action: ActionRead, completed: boolean) => void;
}) {
  const [open, setOpen] = useState(false);
  const tone = toneFor(action);
  const panelId = `action-detail-${action.id}`;

  const hasSteps = (action.steps?.length ?? 0) > 0;
  const hasDetail =
    hasSteps ||
    (action.materials?.length ?? 0) > 0 ||
    (action.check_first?.length ?? 0) > 0 ||
    (action.avoid?.length ?? 0) > 0 ||
    Boolean(action.done_when) ||
    Boolean(action.reason) ||
    Boolean(action.source) ||
    (action.timing != null);

  return (
    <article
      className={cn(
        "rounded-card border shadow-card transition-colors",
        containerClass(action)
      )}
    >
      <div className="flex items-start gap-3 p-4">
        <button
          type="button"
          role="checkbox"
          aria-checked={action.completed}
          aria-label={action.completed ? `Reopen: ${action.title}` : `Mark as done: ${action.title}`}
          disabled={busy}
          onClick={() => onToggle(action, !action.completed)}
          className={cn(
            "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1",
            action.completed
              ? "border-brand-600 bg-brand-600 text-white"
              : "border-border-strong bg-surface text-transparent hover:border-brand-500",
            busy && "opacity-60"
          )}
        >
          <Check className="h-3.5 w-3.5" />
        </button>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3
              className={cn(
                "font-display text-base font-bold tracking-tight text-ink",
                action.completed && "text-ink-muted line-through decoration-ink-muted/40"
              )}
            >
              {action.title}
            </h3>
            {action.priority && (
              <StatusBadge tone={tone}>{PRIORITY_LABELS[action.priority] ?? action.priority}</StatusBadge>
            )}
            {action.completed && <StatusBadge tone="success">Done</StatusBadge>}
          </div>

          <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">{action.explanation}</p>

          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-muted">
            <span className="font-semibold text-ink-soft">
              {CATEGORY_LABELS[action.category] ?? action.category}
            </span>
            {action.timing && (
              <span className="inline-flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                When: {action.timing}
              </span>
            )}
          </div>

          {hasDetail && (
            <button
              type="button"
              onClick={() => setOpen((value) => !value)}
              aria-expanded={open}
              aria-controls={panelId}
              className="mt-2.5 inline-flex items-center gap-1 text-xs font-semibold text-brand-700 transition-colors hover:text-brand-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 rounded"
            >
              <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")} />
              {open ? "Hide steps" : "Show steps"}
            </button>
          )}
        </div>
      </div>

      {hasDetail && open && (
        <div id={panelId} className="space-y-3.5 border-t border-border/70 px-4 pb-4 pt-3.5">
          {hasSteps && (
            <DetailSection icon={<ListOrdered className="h-3.5 w-3.5" />} title="How to do it">
              <ol className="list-decimal space-y-1 pl-5 marker:text-ink-muted/60">
                {action.steps!.map((step, index) => (
                  <li key={index}>{step}</li>
                ))}
              </ol>
            </DetailSection>
          )}

          {(action.materials?.length ?? 0) > 0 && (
            <DetailSection icon={<Package className="h-3.5 w-3.5" />} title="What you need">
              <BulletList items={action.materials!} />
            </DetailSection>
          )}

          {(action.check_first?.length ?? 0) > 0 && (
            <DetailSection
              icon={<Eye className="h-3.5 w-3.5" />}
              title="What to check first"
              tone="warning"
            >
              <BulletList items={action.check_first!} />
            </DetailSection>
          )}

          {(action.avoid?.length ?? 0) > 0 && (
            <DetailSection icon={<Ban className="h-3.5 w-3.5" />} title="What to avoid" tone="avoid">
              <BulletList items={action.avoid!} />
            </DetailSection>
          )}

          {action.done_when && (
            <DetailSection
              icon={<CheckCircle2 className="h-3.5 w-3.5" />}
              title="How you know it is done"
              tone="done"
            >
              {action.done_when}
            </DetailSection>
          )}

          {(action.reason || action.source) && (
            <DetailSection icon={<Info className="h-3.5 w-3.5" />} title="Where this comes from">
              {action.reason && <p>{action.reason}</p>}
              {action.source && (
                <p className="mt-1 text-xs text-ink-muted">
                  <span className="font-semibold text-ink-soft">Source: </span>
                  {action.source}
                </p>
              )}
            </DetailSection>
          )}
        </div>
      )}
    </article>
  );
}
