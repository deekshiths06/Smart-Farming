import { cn } from "../../lib/cn";

interface LogoProps {
  className?: string;
  inverted?: boolean;
  showWordmark?: boolean;
  size?: "sm" | "md" | "lg";
}

const SIZES = {
  sm: { mark: "h-8 w-8", word: "text-base" },
  md: { mark: "h-9 w-9", word: "text-lg" },
  lg: { mark: "h-11 w-11", word: "text-2xl" },
} as const;

export function Logo({ className, inverted = false, showWordmark = true, size = "md" }: LogoProps) {
  const dims = SIZES[size];
  const id = inverted ? "logo-leaf-inv" : "logo-leaf";
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <svg
        viewBox="0 0 44 44"
        className={cn(dims.mark, "shrink-0")}
        role="img"
        aria-label="ANNADATA"
      >
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#6ee7b7" />
            <stop offset="1" stopColor="#047857" />
          </linearGradient>
        </defs>
        <rect width="44" height="44" rx="12" fill={inverted ? "#0b2418" : "#163d29"} />
        <path
          d="M22 35c0-9 0-14 0-18"
          stroke={`url(#${id})`}
          strokeWidth="3"
          strokeLinecap="round"
        />
        <path d="M22 21c0-6-4.5-9.5-10.5-9.5 0 6 4.5 9.5 10.5 9.5Z" fill={`url(#${id})`} />
        <path d="M22 26c0-6 4.5-9.5 10.5-9.5 0 6-4.5 9.5-10.5 9.5Z" fill="#34d399" />
        <circle cx="22" cy="13.5" r="2.6" fill="#a7f3d0" />
      </svg>
      {showWordmark && (
        <span
          className={cn(
            "font-extrabold tracking-tight",
            dims.word,
            inverted ? "text-white" : "text-ink"
          )}
        >
          ANNADATA
        </span>
      )}
    </span>
  );
}
