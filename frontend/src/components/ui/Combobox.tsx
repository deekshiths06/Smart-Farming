import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Check, ChevronDown, Loader2, Search, X } from "lucide-react";
import { cn } from "../../lib/cn";
import { useClickOutside } from "../../hooks/useClickOutside";

export interface ComboboxOption {
  /** Stable value/id for the option. */
  value: string;
  /** Human label shown in the list and the input once selected. */
  label: string;
  /** Optional secondary line (e.g. a category). */
  description?: string;
  /** Optional small tag (e.g. "Disease AI"). */
  badge?: string;
  /** Optional payload carrying the full source object. */
  data?: unknown;
}

interface ComboboxProps {
  id?: string;
  /** The currently selected option, or null. */
  value: ComboboxOption | null;
  onChange: (option: ComboboxOption | null) => void;
  /** Async, case-insensitive search. Called (debounced) as the user types. */
  search: (query: string) => Promise<ComboboxOption[]>;
  label?: string;
  placeholder?: string;
  searchHint?: ReactNode;
  emptyMessage?: string;
  errorMessage?: string;
  disabled?: boolean;
  className?: string;
  /** Cap how many matches are rendered at once (keeps the DOM small). */
  maxVisible?: number;
}

const DEBOUNCE_MS = 180;

export function Combobox({
  id,
  value,
  onChange,
  search,
  label,
  placeholder = "Search…",
  searchHint,
  emptyMessage = "No matches found.",
  errorMessage = "Could not load options. Please try again.",
  disabled = false,
  className,
  maxVisible = 100,
}: ComboboxProps) {
  const reactId = useId();
  const inputId = id ?? `combobox-${reactId}`;
  const listboxId = `${inputId}-listbox`;
  const optionId = (index: number) => `${inputId}-option-${index}`;

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(value?.label ?? "");
  const [options, setOptions] = useState<ComboboxOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const searchRef = useRef(search);
  useEffect(() => {
    searchRef.current = search;
  }, [search]);

  // Keep the input text in sync when the selection is cleared elsewhere.
  useEffect(() => {
    if (value === null && !open) setQuery("");
  }, [value, open]);

  // Debounced async search whenever the query changes while open.
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setFailed(false);
    const handle = setTimeout(() => {
      searchRef
        .current(query)
        .then((result) => {
          if (cancelled) return;
          setOptions(result);
          setActiveIndex(result.length > 0 ? 0 : -1);
        })
        .catch(() => {
          if (cancelled) return;
          setOptions([]);
          setFailed(true);
          setActiveIndex(-1);
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [query, open]);

  const visible = options.slice(0, maxVisible);

  const closeAndRevert = () => {
    setOpen(false);
    setQuery(value?.label ?? "");
    setActiveIndex(-1);
  };

  useClickOutside(containerRef, closeAndRevert, open);

  const select = (option: ComboboxOption) => {
    setQuery(option.label);
    setOpen(false);
    setActiveIndex(-1);
    onChange(option);
  };

  const clear = () => {
    setQuery("");
    setOptions([]);
    setActiveIndex(-1);
    onChange(null);
    setOpen(true);
    inputRef.current?.focus();
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (disabled) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (!open) {
        setOpen(true);
        return;
      }
      setActiveIndex((index) => Math.min(index + 1, visible.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => Math.max(index - 1, 0));
    } else if (event.key === "Enter") {
      if (open && activeIndex >= 0 && activeIndex < visible.length) {
        event.preventDefault();
        select(visible[activeIndex]);
      }
    } else if (event.key === "Escape") {
      if (open) {
        event.preventDefault();
        closeAndRevert();
      }
    } else if (event.key === "Home" && open) {
      event.preventDefault();
      setActiveIndex(0);
    } else if (event.key === "End" && open) {
      event.preventDefault();
      setActiveIndex(visible.length - 1);
    }
  };

  const showClear = !disabled && (query.length > 0 || value !== null);

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      {label && (
        <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium text-ink-soft">
          {label}
        </label>
      )}
      <div className="relative">
        <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-muted">
          <Search className="h-4 w-4" />
        </span>
        <input
          ref={inputRef}
          id={inputId}
          type="text"
          role="combobox"
          autoComplete="off"
          aria-expanded={open}
          aria-controls={listboxId}
          aria-activedescendant={
            open && activeIndex >= 0 && visible[activeIndex]
              ? optionId(activeIndex)
              : undefined
          }
          aria-autocomplete="list"
          aria-label={label ? undefined : "Search crops"}
          disabled={disabled}
          value={query}
          placeholder={placeholder}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          className={cn(
            "h-11 w-full rounded-lg border border-border-strong bg-surface pl-10 text-sm text-ink shadow-soft transition-colors",
            "placeholder:text-ink-muted/70 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/20",
            "disabled:cursor-not-allowed disabled:opacity-60",
            showClear ? "pr-16" : "pr-9"
          )}
        />
        <span className="absolute right-1.5 top-1/2 flex -translate-y-1/2 items-center gap-0.5">
          {showClear && (
            <button
              type="button"
              onClick={clear}
              aria-label="Clear selection"
              className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-surface-sunken hover:text-ink"
            >
              <X className="h-4 w-4" />
            </button>
          )}
          <ChevronDown className="mr-1 h-4 w-4 shrink-0 text-ink-muted" aria-hidden="true" />
        </span>
      </div>

      {searchHint && !open && <div className="mt-1.5 text-xs text-ink-muted">{searchHint}</div>}

      {open && (
        <div className="absolute z-50 mt-1.5 w-full overflow-hidden rounded-lg border border-border bg-surface shadow-pop">
          <ul
            id={listboxId}
            role="listbox"
            aria-label="Crop matches"
            className="max-h-72 overflow-y-auto py-1"
          >
            {loading && (
              <li className="flex items-center gap-2 px-3 py-2.5 text-sm text-ink-muted">
                <Loader2 className="h-4 w-4 animate-spin" /> Searching…
              </li>
            )}
            {!loading && failed && (
              <li className="px-3 py-2.5 text-sm text-red-600">{errorMessage}</li>
            )}
            {!loading && !failed && visible.length === 0 && (
              <li className="px-3 py-2.5 text-sm text-ink-muted">{emptyMessage}</li>
            )}
            {!loading &&
              !failed &&
              visible.map((option, index) => {
                const active = index === activeIndex;
                const selected = value?.value === option.value;
                return (
                  <li
                    key={option.value}
                    id={optionId(index)}
                    role="option"
                    aria-selected={selected}
                    onMouseDown={(event) => event.preventDefault()}
                    onMouseMove={() => setActiveIndex(index)}
                    onClick={() => select(option)}
                    className={cn(
                      "flex cursor-pointer items-center gap-2 px-3 py-2.5 text-sm",
                      active ? "bg-surface-sunken" : "bg-transparent"
                    )}
                  >
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <span className="truncate font-medium text-ink">{option.label}</span>
                        {option.badge && (
                          <span className="shrink-0 rounded-full bg-brand-50 px-2 py-0.5 text-[10px] font-semibold text-brand-700 ring-1 ring-inset ring-brand-600/20">
                            {option.badge}
                          </span>
                        )}
                      </span>
                      {option.description && (
                        <span className="mt-0.5 block truncate text-xs text-ink-muted">
                          {option.description}
                        </span>
                      )}
                    </span>
                    {selected && <Check className="h-4 w-4 shrink-0 text-brand-700" />}
                  </li>
                );
              })}
            {!loading && !failed && options.length > maxVisible && (
              <li className="border-t border-border px-3 py-2 text-xs text-ink-muted">
                Showing the first {maxVisible} of {options.length} matches — keep typing to narrow
                it down.
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
