import { Sprout } from "lucide-react";
import { ImageWithFallback } from "../ui/ImageWithFallback";
import { cropImageUrl } from "../../lib/cropImages";
import { cn } from "../../lib/cn";

interface CropImageProps {
  cropName: string | null | undefined;
  displayName?: string | null;
  className?: string;
  wrapperClassName?: string;
}

/**
 * Renders the verified, crop-specific photograph for a crop. When no verified
 * photo exists — or the bundled file fails to load — it degrades to a neutral
 * placeholder clearly labelled with the crop name, so a wrong or misleading
 * photograph is never shown.
 */
export function CropImage({ cropName, displayName, className, wrapperClassName }: CropImageProps) {
  const src = cropImageUrl(cropName);
  const label = (displayName ?? cropName ?? "Crop").toString().trim() || "Crop";

  const placeholder = (
    <div
      role="img"
      aria-label={`No photo available for ${label}`}
      className={cn(
        "flex flex-col items-center justify-center gap-1.5 bg-gradient-to-br from-forest-800 via-forest-900 to-forest-950 px-3 text-center",
        className,
        wrapperClassName
      )}
    >
      <Sprout className="h-8 w-8 text-brand-300/70" aria-hidden="true" />
      <span className="text-xs font-semibold text-brand-100">{label}</span>
      <span className="text-[10px] uppercase tracking-wide text-brand-200/70">No photo yet</span>
    </div>
  );

  return (
    <ImageWithFallback
      src={src ?? undefined}
      alt={label}
      className={className}
      wrapperClassName={wrapperClassName}
      fallback={placeholder}
    />
  );
}
