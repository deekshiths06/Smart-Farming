import { Link } from "react-router-dom";
import { Droplets, MapPin, Pencil, Sprout, Trash2 } from "lucide-react";
import { cn } from "../../lib/cn";
import { formatArea } from "../../lib/geo";
import {
  AREA_SOURCE_LABELS,
  SOIL_STATUS_LABELS,
  WATER_SOURCE_LABELS,
  landStructure,
} from "../../lib/labels";
import type { Field } from "../../types/field";
import { Card } from "./Card";
import { StatusBadge } from "./StatusBadge";

interface FieldCardProps {
  field: Field;
  onDelete?: (field: Field) => void;
  className?: string;
}

const SOIL_TONE = {
  available: "success",
  pending: "info",
  not_provided: "neutral",
} as const;

export function FieldCard({ field, onDelete, className }: FieldCardProps) {
  const hasPosition = field.latitude !== null && field.longitude !== null;

  return (
    <Card className={cn("flex flex-col", className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
            <Sprout className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <Link
              to={`/fields/${field.id}`}
              className="block truncate font-semibold text-ink transition-colors hover:text-brand-700"
            >
              {field.field_name}
            </Link>
            <p className="mt-0.5 truncate text-xs text-ink-muted">
              {landStructure(field as unknown as { locality?: string | null; sub_district?: string | null; district?: string | null; state?: string | null; country?: string | null })}
            </p>
          </div>
        </div>
        {onDelete && (
          <button
            type="button"
            onClick={() => onDelete(field)}
            title={`Delete ${field.field_name}`}
            aria-label={`Delete ${field.field_name}`}
            className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-red-50 hover:text-red-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2">
        <div className="flex items-center gap-1.5 rounded-lg bg-surface-sunken px-3 py-2 text-sm">
          <MapPin className="h-3.5 w-3.5 shrink-0 text-brand-700" />
          <span className="truncate text-ink-soft">
            {field.area !== null
              ? `${formatArea(field.area)} ${field.area_unit}`
              : "Area not recorded"}
          </span>
          <span className="ml-auto shrink-0 text-[10px] text-ink-muted">
            {field.area !== null ? AREA_SOURCE_LABELS[field.area_source] : ""}
          </span>
        </div>
        <div className="flex items-center gap-1.5 rounded-lg bg-surface-sunken px-3 py-2 text-sm">
          <Droplets className="h-3.5 w-3.5 shrink-0 text-sky-700" />
          <span className="truncate text-ink-soft">
            {field.water_source ? WATER_SOURCE_LABELS[field.water_source] : "Water not recorded"}
          </span>
        </div>
      </div>

      {hasPosition ? (
        <p className="mt-2.5 font-mono text-[11px] text-ink-muted">
          {field.latitude?.toFixed(4)}, {field.longitude?.toFixed(4)}
        </p>
      ) : (
        <p className="mt-2.5 text-[11px] text-ink-muted">No confirmed location yet.</p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <StatusBadge
          tone={field.location_confirmed ? "success" : "warning"}
          dot
        >
          {field.location_confirmed ? "Location confirmed" : "Location pending"}
        </StatusBadge>
        <StatusBadge tone={SOIL_TONE[field.soil_status]}>
          {SOIL_STATUS_LABELS[field.soil_status]}
        </StatusBadge>
      </div>

      <div className="mt-4 flex gap-2 border-t border-border pt-4">
        <Link
          to={`/fields/${field.id}`}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
        >
          View field
        </Link>
        <Link
          to={`/fields/${field.id}/edit`}
          title={`Edit ${field.field_name}`}
          aria-label={`Edit ${field.field_name}`}
          className="flex items-center justify-center rounded-lg border border-border-strong px-3 py-2 text-ink-soft transition-colors hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
        >
          <Pencil className="h-4 w-4" />
        </Link>
      </div>
    </Card>
  );
}