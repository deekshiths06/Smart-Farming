import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

export type BadgeTone = "success" | "warning" | "info" | "neutral" | "danger" | "brand";

const TONES: Record<BadgeTone, string> = {
  success: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  warning: "bg-amber-50 text-amber-700 ring-amber-600/20",
  info: "bg-sky-50 text-sky-700 ring-sky-600/20",
  neutral: "bg-surface-sunken text-ink-soft ring-border-strong",
  danger: "bg-red-50 text-red-700 ring-red-600/20",
  brand: "bg-brand-50 text-brand-800 ring-brand-600/20",
};

interface StatusBadgeProps {
  tone?: BadgeTone;
  children: ReactNode;
  dot?: boolean;
  icon?: ReactNode;
  className?: string;
}

export function StatusBadge({
  tone = "neutral",
  children,
  dot = false,
  icon,
  className,
}: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset",
        TONES[tone],
        className
      )}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" aria-hidden="true" />}
      {icon}
      {children}
    </span>
  );
}
