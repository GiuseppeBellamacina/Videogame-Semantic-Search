import { useEffect, useRef } from "react";
import { Play, X, Eraser } from "lucide-react";
import { Dropdown } from "@/components/Dropdown";

/** Shown in the editor until the user writes something of their own. */
export const DEFAULT_QUERY = `CONSTRUCT {
  ?g vg:developedBy ?dev .
  ?g vg:publishedBy ?pub .
  ?g vg:belongsTo ?serie .
  ?g vg:madeWith ?motore .
  ?g vg:hasGenre ?genere .
}
WHERE {
  VALUES ?titolo {
    "The Legend of Zelda: Breath of the Wild" "The Legend of Zelda: Tears of the Kingdom"
    "The Legend of Zelda: Twilight Princess" "The Legend of Zelda: Skyward Sword"
    "Cyberpunk 2077" "The Witcher 3: Wild Hunt"
    "Grand Theft Auto V" "Grand Theft Auto VI" "Red Dead Redemption 2"
    "Fallout: New Vegas" "Fallout 4"
    "Dark Souls III" "Elden Ring"
    "Death Stranding" "Resident Evil 4"
    "Crimson Desert" "Horizon Zero Dawn" "Horizon Forbidden West"
  }
  ?g vg:gameName ?titolo .
  { ?g vg:developedBy ?dev }
  UNION { ?g vg:publishedBy ?pub }
  UNION { ?g vg:belongsTo ?serie }
  UNION { ?g vg:madeWith ?motore }
  UNION { ?g vg:hasGenre ?genere }
}`;

const EXAMPLES: { label: string; query: string }[] = [
  {
    label: "Grafo di giochi famosi (Zelda, Cyberpunk, GTA, Fallout, Horizon…)",
    query: DEFAULT_QUERY,
  },
  {
    label: "Top 10 per punteggio Metacritic",
    query: `SELECT ?name ?score WHERE {
  ?g a vg:VideoGame ;
     vg:gameName ?name ;
     vg:metacriticScore ?score .
}
ORDER BY DESC(?score)
LIMIT 10`,
  },
  {
    label: "Giochi di FromSoftware e i loro generi (grafo)",
    query: `CONSTRUCT {
  ?g vg:developedBy ?d .
  ?g vg:hasGenre ?genre .
}
WHERE {
  ?d vg:developerName "FromSoftware" .
  ?g vg:developedBy ?d ;
     vg:hasGenre ?genre .
}
LIMIT 200`,
  },
  {
    label: "Giochi per genere (conteggio)",
    query: `SELECT ?genreName (COUNT(DISTINCT ?g) AS ?n) WHERE {
  ?g vg:hasGenre ?genre .
  ?genre vg:genreName ?genreName .
}
GROUP BY ?genreName
ORDER BY DESC(?n)
LIMIT 15`,
  },
  {
    label: "Molto recensiti usciti in ottobre 2023",
    query: `SELECT ?name ?date ?score WHERE {
  ?g a vg:HighlyRatedGame ;
     vg:gameName ?name ;
     vg:releaseDate ?date ;
     vg:metacriticScore ?score .
  FILTER(YEAR(?date) = 2023 && MONTH(?date) = 10)
}
ORDER BY DESC(?score)`,
  },
  {
    label: "Giochi pubblicati da Sony su 3+ piattaforme",
    query: `SELECT ?name WHERE {
  ?g a vg:SonyPublishedGame, vg:MultiPlatformGame ;
     vg:gameName ?name .
}
ORDER BY ?name
LIMIT 50`,
  },
  {
    label: "Esiste un vincitore Game of the Year? (ASK)",
    query: `ASK { ?g a vg:GOTYWinner }`,
  },
];

interface SparqlEditorProps {
  value: string;
  onChange: (v: string) => void;
  onRun: (query: string) => void;
  onCancel: () => void;
  loading: boolean;
}

/** Free SPARQL: a plain editor, Ctrl+Enter runs it, standard prefixes are added by the server. */
export function SparqlEditor({ value, onChange, onRun, onCancel, loading }: SparqlEditorProps) {
  const area = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = area.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(Math.max(el.scrollHeight, 150), 340)}px`;
    }
  }, [value]);

  const run = () => {
    if (value.trim() && !loading) onRun(value);
  };

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      run();
    } else if (e.key === "Tab") {
      // a tab inside the query, not a jump to the next control
      e.preventDefault();
      const el = e.currentTarget;
      const { selectionStart: s, selectionEnd: t } = el;
      onChange(`${value.slice(0, s)}  ${value.slice(t)}`);
      requestAnimationFrame(() => el.setSelectionRange(s + 2, s + 2));
    }
  };

  return (
    <div className="rounded-sm border border-rule bg-panel/60">
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 pt-3.5">
        <h2 className="font-serif text-xl">Scrivi una query SPARQL</h2>
        <Dropdown
          className="w-72"
          value=""
          placeholder="Parti da un esempio…"
          options={EXAMPLES.map((e, i) => ({ value: String(i), label: e.label }))}
          onChange={(i) => onChange(EXAMPLES[Number(i)].query)}
          ariaLabel="Esempi di query"
        />
      </div>
      <div className="px-4 py-3">
        <textarea
          ref={area}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKey}
          spellCheck={false}
          autoCapitalize="off"
          autoCorrect="off"
          placeholder={"SELECT ?name WHERE {\n  ?g a vg:VideoGame ; vg:gameName ?name .\n} LIMIT 10"}
          aria-label="Query SPARQL"
          className="block w-full resize-y rounded-sm border border-rule bg-black/40 p-3 font-mono text-[13px] leading-relaxed text-ink placeholder:text-mute focus:border-mute focus:outline-none"
        />
        <p className="mt-2 text-[12px] text-mute">
          I prefissi <span className="font-mono">vg: rdf: rdfs: xsd: owl: wd: dcterms:</span> sono aggiunti da soli.
          Solo lettura (SELECT, CONSTRUCT, ASK, DESCRIBE), al massimo 1000 righe, 30 secondi.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3 border-t border-rule px-4 py-3">
        <button onClick={() => onChange("")} className="btn h-9" disabled={!value}>
          <Eraser className="h-3.5 w-3.5" /> Svuota
        </button>
        <span className="ml-auto flex items-center gap-3">
          <span className="hidden font-mono text-[11px] text-mute sm:inline">Ctrl + Invio</span>
          {loading ? (
            <button onClick={onCancel} className="btn h-9">
              <X className="h-4 w-4" /> Annulla
            </button>
          ) : (
            <button onClick={run} disabled={!value.trim()} className="btn btn-primary h-9">
              <Play className="h-4 w-4" /> Esegui
            </button>
          )}
        </span>
      </div>
    </div>
  );
}
