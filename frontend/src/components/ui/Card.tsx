import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "../../lib/cn";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  interactive?: boolean;
  padded?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(function Card(
  { interactive = false, padded = true, className, ...rest },
  ref
) {
  return (
    <div
      ref={ref}
      className={cn(
        "rounded-card border border-border bg-surface shadow-card",
        padded && "p-5",
        interactive &&
          "transition duration-200 hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-pop",
        className
      )}
      {...rest}
    />
  );
});
