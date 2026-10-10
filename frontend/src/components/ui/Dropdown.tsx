import { useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { cn } from "../../lib/cn";
import { useClickOutside } from "../../hooks/useClickOutside";

interface DropdownProps {
  label?: string;
  trigger: ReactNode;
  children: ReactNode | ((close: () => void) => ReactNode);
  align?: "left" | "right";
  panelClassName?: string;
  chevron?: boolean;
}

export function Dropdown({
  label,
  trigger,
  children,
  align = "right",
  panelClassName,
  chevron = false,
}: DropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false), open);

  const close = () => setOpen(false);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={label}
        className="inline-flex items-center gap-1.5 rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
      >
        {trigger}
        {chevron && (
          <ChevronDown
            className={cn("h-4 w-4 text-ink-muted transition-transform", open && "rotate-180")}
          />
        )}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            role="menu"
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.14, ease: "easeOut" }}
            className={cn(
              "absolute z-50 mt-2 overflow-hidden rounded-lg border border-border bg-surface py-1.5 shadow-pop",
              align === "right" ? "right-0" : "left-0",
              panelClassName
            )}
          >
            {typeof children === "function" ? children(close) : children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}