import { useEffect, useRef, useState } from "react";
import { suggest } from "@/lib/api";
import type { Suggestion } from "@/types";

const TYPE_LABELS: Record<string, string> = {
  VideoGame: "Gioco",
  Developer: "Developer",
  Publisher: "Publisher",
  Genre: "Genere",
  Platform: "Piattaforma",
  Franchise: "Serie",
  Character: "Personaggio",
  Award: "Premio",
  GameEngine: "Engine",
  GameMode: "Modalità",
};

interface SuggestInputProps {
  value: string;
  onChange: (value: string) => void;
  /** Called when the user picks a suggestion (the text is already replaced). */
  onPick?: (s: Suggestion) => void;
  /** Restrict suggestions to these entity types. */
  types?: string[];
  /** Static items shown when the input is empty (e.g. example questions). */
  examples?: string[];
  /** Called on Enter when no suggestion is highlighted. */
  onSubmit?: () => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

/** Text input with live autosuggest on the trailing words of what is typed. */
export function SuggestInput({
  value,
  onChange,
  onPick,
  types,
  examples,
  onSubmit,
  placeholder,
  disabled,
  className,
}: SuggestInputProps) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Suggestion[]>([]);
  const [match, setMatch] = useState("");
  const [active, setActive] = useState(-1);
  const skipNext = useRef(false);
  const typesKey = types?.join(",") ?? "";

  useEffect(() => {
    if (skipNext.current) {
      skipNext.current = false;
      return;
    }
    if (value.trim().length < 2) {
      setItems([]);
      setMatch("");
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const res = await suggest(value, typesKey, controller.signal);
        setItems(res.suggestions);
        setMatch(res.match);
        setActive(-1);
      } catch {
        /* aborted or backend unavailable: no suggestions */
      }
    }, 180);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [value, typesKey]);

  const pick = (s: Suggestion) => {
    // replace the matched trailing words with the full label
    const head = match ? value.slice(0, value.lastIndexOf(match)) : "";
    skipNext.current = true;
    onChange(head + s.label);
    onPick?.(s);
    setItems([]);
    setOpen(false);
  };

  const showExamples = value.trim().length < 2 && !!examples?.length;
  const list = showExamples ? [] : items;

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown" && list.length) {
      e.preventDefault();
      setActive((a) => (a + 1) % list.length);
    } else if (e.key === "ArrowUp" && list.length) {
      e.preventDefault();
      setActive((a) => (a <= 0 ? list.length - 1 : a - 1));
    } else if ((e.key === "Enter" || e.key === "Tab") && active >= 0 && list[active]) {
      e.preventDefault();
      pick(list[active]);
    } else if (e.key === "Enter" && onSubmit) {
      e.preventDefault();
      setOpen(false);
      onSubmit();
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div className="relative w-full">
      <input
        type="text"
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete="off"
        className={className}
      />
      {open && !disabled && (list.length > 0 || showExamples) && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl overflow-y-auto max-h-72 z-50 animate-fade-in">
          {showExamples ? (
            <>
              <div className="px-4 py-2 text-xs text-gray-500 uppercase tracking-wide border-b border-gray-800">
                Suggerimenti
              </div>
              {examples!.map((ex) => (
                <button
                  key={ex}
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => {
                    onChange(ex);
                    setOpen(false);
                    onSubmit?.();
                  }}
                  className="w-full px-4 py-3 text-left text-sm text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
                >
                  {ex}
                </button>
              ))}
            </>
          ) : (
            list.map((s, i) => (
              <button
                key={s.uri}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => pick(s)}
                className={`w-full px-4 py-2.5 text-left flex items-center justify-between gap-3 transition-colors ${
                  i === active ? "bg-gray-800 text-white" : "text-gray-300 hover:bg-gray-800"
                }`}
              >
                <span className="text-sm truncate">{s.label}</span>
                <span className="text-xs text-gray-500 flex-shrink-0">
                  {TYPE_LABELS[s.type] ?? s.type}
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
