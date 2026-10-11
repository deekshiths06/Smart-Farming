import { useState, type ImgHTMLAttributes, type ReactNode } from "react";
import { Sprout } from "lucide-react";
import { cn } from "../../lib/cn";

interface ImageWithFallbackProps extends ImgHTMLAttributes<HTMLImageElement> {
  wrapperClassName?: string;
  /** Optional custom placeholder rendered when `src` is missing or fails to load. */
  fallback?: ReactNode;
}

/**
 * Renders an image and gracefully degrades to a branded gradient panel if the
 * asset fails to load (offline, blocked, missing). Keeps layout stable.
 */
export function ImageWithFallback({
  src,
  alt = "",
  className,
  wrapperClassName,
  fallback,
  ...rest
}: ImageWithFallbackProps) {
  const [failed, setFailed] = useState(false);

  if (failed || !src) {
    if (fallback) return <>{fallback}</>;
    return (
      <div
        role="img"
        aria-label={alt || "Decorative agricultural image"}
        className={cn(
          "flex items-center justify-center bg-gradient-to-br from-forest-800 via-forest-900 to-forest-950",
          className,
          wrapperClassName
        )}
      >
        <Sprout className="h-12 w-12 text-brand-300/60" aria-hidden="true" />
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
      className={cn(className, wrapperClassName)}
      {...rest}
    />
  );
}
