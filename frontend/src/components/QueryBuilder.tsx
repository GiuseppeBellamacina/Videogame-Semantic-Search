import { useEffect, useMemo, useRef, useState } from "react";
import { Plus, X, ArrowRight, Loader2 } from "lucide-react";
import { countBuilder, getBuilderSchema } from "@/lib/api";
import { SuggestInput } from "@/components/SuggestInput";
import type { BuilderField, BuilderRequest, BuilderSchema } from "@/types";

interface Cond {
  id: number;
  field: string;
  op: string;
  value: string; // entity URI (picked suggestion), number or free text
  display: string; // what the input shows
}

const OP_LABELS: Record<string, string> = {
  is: "è",
  is_not: "non è",
  contains: "contiene",
  equals: "uguale a",
  "=": "=",
  ">=": "≥",
  "<=": "≤",
  ">": ">",
  "<": "<",
};
const ORDER_LABELS: Record<string, string> = {
  name: "titolo",
  score_desc: "punteggio",
  date_desc: "più recenti",
  date_asc: "più vecchi",
};
const FIELD_VERB: Record<string, string> = {
  developedBy: "sviluppato da",
  publishedBy: "pubblicato da",
  hasGenre: "genere",
  availableOn: "su",
  belongsTo: "serie",
  hasCharacter: "con personaggio",
  wonAward: "premio",
  madeWith: "motore",
  hasGameMode: "modalità",
  metacriticScore: "punteggio",
  releaseYear: "anno di uscita",
  gameName: "titolo",
  countryOfOrigin: "paese",
  isA: "categoria",
};

const sel =
  "bg-transparent text-sm text-ink focus:outline-none cursor-pointer [&>option]:bg-panel";

interface QueryBuilderProps {
  onRun: (body: BuilderRequest) => void;
  onCancel: () => void;
  loading: boolean;
}

let nextId = 1;

export function QueryBuilder({ onRun, onCancel, loading }: QueryBuilderProps) {
  const [schema, setSchema] = useState<BuilderSchema | null>(null);
  const [schemaError, setSchemaError] = useState(false);
  const [conds, setConds] = useState<Cond[]>([]);
  const [menu, setMenu] = useState(false);
  const [orderBy, setOrderBy] = useState("name");
  const [limit, setLimit] = useState(50);
  const [output, setOutput] = useState<"table" | "graph">("table");
  const [count, setCount] = useState<number | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getBuilderSchema().then(setSchema).catch(() => setSchemaError(true));
  }, []);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) setMenu(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const field = (name: string): BuilderField | undefined =>
    schema?.fields.find((f) => f.field === name);

  const filters = useMemo(
    () =>
      conds
        .filter((c) => c.value.trim() !== "")
        .map((c) => {
          const kind = field(c.field)?.kind;
          return {
            field: c.field,
            op: c.op,
            value: kind === "number" || kind === "year" ? Number(c.value) : c.value,
          };
        }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [conds, schema],
  );

  // live preview: how many games match, debounced
  useEffect(() => {
    if (!schema) return;
    setCount(null);
    const c = new AbortController();
    const t = setTimeout(() => {
      countBuilder(filters, c.signal)
        .then((n) => setCount(n))
        .catch(() => {});
    }, 300);
    return () => {
      clearTimeout(t);
      c.abort();
    };
  }, [filters, schema]);

  const add = (f: BuilderField) => {
    setConds((c) => [
      ...c,
      {
        id: nextId++,
        field: f.field,
        op: f.ops[0],
        value: f.kind === "class" ? f.options![0] : "",
        display: "",
      },
    ]);
    setMenu(false);
  };
  const patch = (id: number, p: Partial<Cond>) =>
    setConds((c) => c.map((x) => (x.id === id ? { ...x, ...p } : x)));
  const drop = (id: number) => setConds((c) => c.filter((x) => x.id !== id));

  if (schemaError)
    return <p className="text-sm text-brick">Impossibile caricare i filtri. Il backend è attivo?</p>;
  if (!schema) return <Loader2 className="h-4 w-4 animate-spin text-mute" />;

  const run = () => onRun({ filters, order_by: orderBy, limit, output });
  const noMatch = count === 0;

  return (
    <div>
      {/* the query reads as a sentence */}
      <div className="flex min-h-11 flex-wrap items-center gap-x-2 gap-y-2 rounded-sm border border-rule bg-panel px-3 py-2">
        <span className="font-serif text-lg">Cerca videogiochi</span>

        {conds.map((c) => {
          const f = field(c.field)!;
          return (
            <span
              key={c.id}
              className="group inline-flex items-center gap-1.5 rounded-sm border border-rule bg-raised py-0.5 pl-2.5 pr-1 animate-fade-in"
            >
              <select
                value={c.field}
                onChange={(e) => {
                  const nf = field(e.target.value)!;
                  patch(c.id, {
                    field: nf.field,
                    op: nf.ops[0],
                    value: nf.kind === "class" ? nf.options![0] : "",
                    display: "",
                  });
                }}
                className={`${sel} text-mute`}
                aria-label="Campo"
              >
                {schema.fields.map((x) => (
                  <option key={x.field} value={x.field}>
                    {FIELD_VERB[x.field] ?? x.label}
                  </option>
                ))}
              </select>
              {f.ops.length > 1 && (
                <select
                  value={c.op}
                  onChange={(e) => patch(c.id, { op: e.target.value })}
                  className={`${sel} text-brick`}
                  aria-label="Operatore"
                >
                  {f.ops.map((op) => (
                    <option key={op} value={op}>
                      {OP_LABELS[op] ?? op}
                    </option>
                  ))}
                </select>
              )}
              {f.kind === "entity" ? (
                <div className="w-40">
                  <SuggestInput
                    value={c.display}
                    types={[f.target!]}
                    onChange={(v) => patch(c.id, { display: v, value: v })}
                    onPick={(s) => patch(c.id, { value: s.uri, display: s.label })}
                    placeholder={f.label.toLowerCase()}
                    className="w-full bg-transparent text-sm placeholder:text-mute focus:outline-none"
                  />
                </div>
              ) : f.kind === "class" ? (
                <select
                  value={c.value}
                  onChange={(e) => patch(c.id, { value: e.target.value })}
                  className={sel}
                  aria-label="Categoria"
                >
                  {f.options!.map((o) => (
                    <option key={o} value={o}>
                      {o}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={f.kind === "text" ? "text" : "number"}
                  value={c.value}
                  onChange={(e) => patch(c.id, { value: e.target.value, display: e.target.value })}
                  placeholder={f.kind === "year" ? "2023" : f.kind === "number" ? "85" : "testo"}
                  className="w-20 bg-transparent text-sm placeholder:text-mute focus:outline-none"
                />
              )}
              <button
                onClick={() => drop(c.id)}
                className="rounded-sm p-1 text-mute hover:bg-rule hover:text-ink"
                aria-label="Rimuovi condizione"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          );
        })}

        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenu((m) => !m)}
            className="inline-flex items-center gap-1 rounded-sm border border-dashed border-rule px-2 py-0.5 text-sm text-mute transition-colors hover:border-brick hover:text-ink"
            aria-expanded={menu}
          >
            <Plus className="h-3.5 w-3.5" /> {conds.length ? "condizione" : "aggiungi una condizione"}
          </button>
          {menu && (
            <ul className="absolute left-0 top-full z-50 mt-1.5 max-h-72 w-52 overflow-y-auto rounded-sm border border-rule bg-panel py-1 shadow-[0_12px_32px_-8px_rgba(0,0,0,0.6)] animate-fade-in">
              {schema.fields.map((f) => (
                <li key={f.field}>
                  <button
                    onClick={() => add(f)}
                    className="w-full px-3 py-1.5 text-left text-sm hover:bg-raised"
                  >
                    {f.label}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-[13px] text-mute">
        <span className="font-mono text-xs" aria-live="polite">
          {count === null ? "…" : noMatch ? "nessun gioco" : `${count.toLocaleString("it-IT")} giochi`}
        </span>
        <label className="flex items-center gap-1.5">
          ordina per
          <select value={orderBy} onChange={(e) => setOrderBy(e.target.value)} className={`${sel} text-ink`}>
            {schema.orders.map((o) => (
              <option key={o} value={o}>
                {ORDER_LABELS[o] ?? o}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-1.5">
          max
          <input
            type="number"
            min={1}
            max={500}
            value={limit}
            onChange={(e) => setLimit(Math.max(1, Math.min(500, Number(e.target.value) || 1)))}
            className="w-14 bg-transparent text-ink focus:outline-none"
          />
        </label>
        <label className="flex items-center gap-1.5">
          mostra
          <select
            value={output}
            onChange={(e) => setOutput(e.target.value as "table" | "graph")}
            className={`${sel} text-ink`}
          >
            <option value="table">elenco</option>
            <option value="graph">relazioni</option>
          </select>
        </label>
        <span className="ml-auto">
          {loading ? (
            <button onClick={onCancel} className="btn">
              <X className="h-4 w-4" /> Annulla
            </button>
          ) : (
            <button onClick={run} disabled={noMatch} className="btn btn-primary">
              Mostra <ArrowRight className="h-4 w-4" />
            </button>
          )}
        </span>
      </div>
    </div>
  );
}
