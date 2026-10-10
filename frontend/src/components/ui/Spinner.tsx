import { cn } from "../../lib/cn";

interface SpinnerProps {
  className?: string;
  label?: string;
}

export function Spinner({ className, label }: SpinnerProps) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-sm text-ink-muted", className)} role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      {label && <span>{label}</span>}
    </span>
  );
}
