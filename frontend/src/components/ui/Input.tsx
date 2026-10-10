import { forwardRef, type InputHTMLAttributes, type ReactNode } from "react";
import { cn } from "../../lib/cn";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: ReactNode;
  error?: string;
  leadingIcon?: ReactNode;
  trailing?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { id, label, hint, error, leadingIcon, trailing, className, ...rest },
  ref
) {
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  return (
    <div className="w-full">
      {label && (
        <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-ink-soft">
          {label}
        </label>
      )}
      <div className="relative">
        {leadingIcon && (
          <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-muted">
            {leadingIcon}
          </span>
        )}
        <input
          id={id}
          ref={ref}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={cn(
            "h-11 w-full rounded-lg border bg-surface text-sm text-ink shadow-soft transition-colors placeholder:text-ink-muted/70 focus:outline-none",
            "border-border-strong focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20",
            error && "border-red-400 focus:border-red-500 focus:ring-red-500/20",
            leadingIcon ? "pl-10" : "pl-3.5",
            trailing ? "pr-11" : "pr-3.5",
            className
          )}
          {...rest}
        />
        {trailing && (
          <span className="absolute right-1.5 top-1/2 -translate-y-1/2">{trailing}</span>
        )}
      </div>
      {error ? (
        <p id={`${id}-error`} className="mt-1.5 text-xs font-medium text-red-600">
          {error}
        </p>
      ) : hint ? (
        <div id={`${id}-hint`} className="mt-1.5 text-xs text-ink-muted">
          {hint}
        </div>
      ) : null}
    </div>
  );
});
