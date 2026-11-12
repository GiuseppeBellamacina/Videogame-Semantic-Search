import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Search } from "lucide-react";

export interface DropdownOption {
  value: string;
  label: string;
  hint?: string;
}

interface DropdownProps {
  value: string;
  options: DropdownOption[];
  onChange: (value: string) => void;
  placeholder?: string;
  /** Show a filter box (useful past ~10 options). */
  searchable?: boolean;
  className?: string;
  buttonClassName?: string;
  ariaLabel?: string;
}

/** Small themed listbox: replaces the native <select>, which ignores the dark theme. */
export function Dropdown({
  value,
  options,
  onChange,
  placeholder = "Scegli",
  searchable,
  className = "",
  buttonClassName = "",
  ariaLabel,
}: DropdownProps) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const shown = useMemo(() => {
    const s = q.trim().toLowerCase();
    return s ? options.filter((o) => o.label.toLowerCase().includes(s)) : options;
  }, [options, q]);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  useEffect(() => {
    if (open) {
      setQ("");
      setActive(Math.max(0, options.findIndex((o) => o.value === value)));
      if (searchable) setTimeout(() => searchRef.current?.focus(), 0);
    }
  }, [open, options, value, searchable]);

  const pick = (o: DropdownOption) => {
    onChange(o.value);
    setOpen(false);
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") setOpen(false);
    else if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(shown.length - 1, a + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (e.key === "Enter" && shown[active]) {
      e.preventDefault();
      pick(shown[active]);
    }
  };

  const current = options.find((o) => o.value === value);

  return (
    <div ref={root} className={`relative ${className}`} onKeyDown={open ? onKey : undefined}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel}
        className={`inline-flex h-9 w-full items-center justify-between gap-2 rounded-sm border border-rule bg-panel px-3 text-left text-sm transition-colors hover:border-mute focus-visible:border-mute ${buttonClassName}`}
      >
        <span className={`truncate ${current ? "text-ink" : "text-mute"}`}>
          {current?.label ?? placeholder}
        </span>
        <ChevronDown className={`h-3.5 w-3.5 flex-shrink-0 text-mute transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 min-w-full max-w-[320px] animate-fade-in rounded-sm border border-rule bg-panel shadow-[0_16px_40px_-8px_rgba(0,0,0,0.7)]">
          {searchable && (
            <div className="flex items-center gap-2 border-b border-rule px-3 py-2">
              <Search className="h-3.5 w-3.5 text-mute" />
              <input
                ref={searchRef}
                value={q}
                onChange={(e) => {
                  setQ(e.target.value);
                  setActive(0);
                }}
                placeholder="Cerca…"
                className="w-full bg-transparent text-sm placeholder:text-mute focus:outline-none"
              />
            </div>
          )}
          <ul role="listbox" className="max-h-64 overflow-y-auto py-1">
            {shown.length === 0 && <li className="px-3 py-2 text-sm text-mute">Nessun risultato</li>}
            {shown.map((o, i) => (
              <li key={o.value} role="option" aria-selected={o.value === value}>
                <button
                  type="button"
                  onMouseEnter={() => setActive(i)}
                  onClick={() => pick(o)}
                  className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm ${i === active ? "bg-raised" : ""}`}
                >
                  <span className="flex-1 truncate">{o.label}</span>
                  {o.hint && <span className="font-mono text-[11px] text-mute">{o.hint}</span>}
                  {o.value === value && <Check className="h-3.5 w-3.5 text-brick" />}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
