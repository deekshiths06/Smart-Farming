import { AlertTriangle, RefreshCw } from "lucide-react";
import { cn } from "../../lib/cn";

interface ErrorAlertProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
}

export function ErrorAlert({
  title = "Something went wrong",
  message,
  onRetry,
  retryLabel = "Try again",
  className,
}: ErrorAlertProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-3 rounded-card border border-red-200 bg-red-50 p-4 text-left",
        className
      )}
    >
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-red-100 text-red-600">
        <AlertTriangle className="h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-red-800">{title}</p>
        <p className="mt-0.5 text-sm leading-relaxed text-red-700">{message}</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-red-300 bg-white px-3 py-1.5 text-xs font-semibold text-red-700 transition-colors hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
          >
            <RefreshCw className="h-3.5 w-3.5" /> {retryLabel}
          </button>
        )}
      </div>
    </div>
  );
}
