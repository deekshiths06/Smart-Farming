import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { Logo } from "./ui/Logo";
import { ImageWithFallback } from "./ui/ImageWithFallback";

const FEATURES = [
  "GPS-confirmed field location — never a guess",
  "Live weather read from the field itself",
  "Honest records — nothing invented",
];

interface AuthLayoutProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
}

export default function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen bg-canvas lg:grid lg:grid-cols-[1.05fr_1fr]">
      <div className="relative hidden overflow-hidden lg:block">
        <ImageWithFallback
          src="/assets/login-hero.jpg"
          alt="Lush green crop field stretching toward the horizon"
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-forest-950 via-forest-950/75 to-forest-900/35" aria-hidden="true" />
        <div className="absolute inset-0 flex flex-col p-10 xl:p-14">
          <Logo inverted showWordmark size="md" />
          <div className="mt-auto max-w-md">
            <h2 className="text-3xl font-bold leading-tight text-white xl:text-4xl">
              Intelligent farming. Better decisions.
            </h2>
            <p className="mt-4 text-[15px] leading-relaxed text-white/80">
              ANNADATA builds a trusted record of your fields — real location, honest area and
              live weather — so every recommendation starts from truth.
            </p>
            <ul className="mt-8 space-y-3">
              {FEATURES.map((feature) => (
                <li key={feature} className="flex items-center gap-3 text-sm text-white/90">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white/10 ring-1 ring-white/20">
                    <Check className="h-4 w-4 text-brand-300" />
                  </span>
                  {feature}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <div className="relative flex min-h-screen flex-col">
        <div className="flex items-center justify-between border-b border-border bg-surface/60 px-6 py-4 lg:hidden">
          <Link to="/" aria-label="ANNADATA home">
            <Logo size="sm" />
          </Link>
          <Link to="/" className="text-sm font-medium text-ink-muted transition-colors hover:text-ink">
            Home
          </Link>
        </div>

        <div className="flex flex-1 items-center justify-center px-6 py-10 sm:px-10">
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="w-full max-w-[440px]"
          >
            <div className="hidden lg:block">
              <Logo size="md" />
            </div>
            <h1 className="mt-6 text-[26px] font-bold tracking-tight text-ink sm:text-3xl">{title}</h1>
            {subtitle && <p className="mt-2 text-sm leading-relaxed text-ink-muted">{subtitle}</p>}
            <div className="mt-8">{children}</div>
          </motion.div>
        </div>

        <p className="px-6 pb-6 text-center text-xs text-ink-muted">
          © {new Date().getFullYear()} ANNADATA · Intelligent farming, better decisions.
        </p>
      </div>
    </div>
  );
}