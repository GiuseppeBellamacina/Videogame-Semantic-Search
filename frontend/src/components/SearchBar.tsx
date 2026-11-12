import { useEffect, useState } from "react";
import { ArrowRight, Loader2, Search, X } from "lucide-react";
import { SUGGESTIONS } from "@/lib/queryCache";
import { SuggestInput } from "@/components/SuggestInput";
import type { SearchProgress } from "@/types";

interface SearchBarProps {
  onSearch: (query: string) => void;
  onCancel: () => void;
  loading: boolean;
  progress: SearchProgress | null;
  /** Text to put in the box (e.g. an example picked elsewhere). */
  seed?: string;
}

const STEPS = ["generating", "validating", "executing", "building_graph"] as const;

function statusText(p: SearchProgress | null): string {
  if (!p) return "Avvio la ricerca…";
  if (p.retry === "syntax") return "La query non era valida: la riscrivo…";
  if (p.retry === "error") return "Errore nell'esecuzione: riprovo con un'altra query…";
  if (p.retry === "empty") return "Nessun risultato: allargo la ricerca…";
  switch (p.phase) {
    case "generating":
      return p.attempt > 1
        ? `Scrivo una nuova query (tentativo ${p.attempt})…`
        : "Scrivo la query SPARQL…";
    case "validating":
      return "Controllo la sintassi…";
    case "executing":
      return "Interrogo il grafo…";
    case "building_graph":
      return "Costruisco il grafo…";
  }
}

function useElapsed(active: boolean) {
  const [s, setS] = useState(0);
  useEffect(() => {
    if (!active) return setS(0);
    const t0 = Date.now();
    const id = setInterval(() => setS(Math.floor((Date.now() - t0) / 1000)), 500);
    return () => clearInterval(id);
  }, [active]);
  return s;
}

export function SearchBar({ onSearch, onCancel, loading, progress, seed }: SearchBarProps) {
  const [query, setQuery] = useState("");
  useEffect(() => {
    if (seed) setQuery(seed);
  }, [seed]);
  const elapsed = useElapsed(loading);

  const submit = (q: string = query) => {
    if (q.trim() && !loading) onSearch(q.trim());
  };
  const step = progress ? STEPS.indexOf(progress.phase) : -1;

  return (
    <div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="flex items-stretch gap-2"
      >
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-mute" />
          <SuggestInput
            value={query}
            onChange={setQuery}
            examples={SUGGESTIONS}
            onSubmit={() => submit()}
            placeholder="Chiedi qualcosa: «giochi FromSoftware su PlayStation»"
            disabled={loading}
            className="h-11 w-full rounded-sm border border-rule bg-panel pl-10 pr-3 text-[15px] text-ink placeholder:text-mute focus:border-brick focus:outline-none disabled:opacity-70"
          />
        </div>
        {loading ? (
          <button type="button" onClick={onCancel} className="btn h-11">
            <X className="h-4 w-4" /> Annulla
          </button>
        ) : (
          <button type="submit" disabled={!query.trim()} className="btn btn-primary h-11">
            Cerca <ArrowRight className="h-4 w-4" />
          </button>
        )}
      </form>

      {/* what the agent is doing right now */}
      <div className="mt-2 h-5 text-[13px] text-mute" aria-live="polite">
        {loading && (
          <span className="flex items-center gap-3 animate-fade-in">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-brick" />
            <span>{statusText(progress)}</span>
            <span className="flex gap-1" aria-hidden>
              {STEPS.map((_, i) => (
                <span
                  key={i}
                  className={`h-0.5 w-5 transition-colors ${i <= step ? "bg-brick" : "bg-rule"}`}
                />
              ))}
            </span>
            <span className="font-mono text-[11px]">{elapsed}s</span>
          </span>
        )}
      </div>
    </div>
  );
}
