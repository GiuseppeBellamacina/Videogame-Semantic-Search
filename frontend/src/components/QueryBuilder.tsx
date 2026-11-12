import { useEffect, useMemo, useRef, useState } from "react";
import { Plus, X, ArrowRight, Loader2, Network, List, SlidersHorizontal } from "lucide-react";
import { countBuilder, getBuilderSchema } from "@/lib/api";
import { SuggestInput } from "@/components/SuggestInput";
import { Dropdown } from "@/components/Dropdown";
import type { BuilderField, BuilderRequest, BuilderSchema } from "@/types";

interface Cond {
  id: number;
  field: string;
  op: string;
  value: string; // entity URI (picked suggestion), number, class name or free text
  display: string; // what the input shows
}

const OP_LABELS: Record<string, string> = {
  is: "è",
  is_not: "non è",
  contains: "contiene",
  equals: "uguale a",
  "=": "uguale a",
  ">=": "almeno",
  "<=": "al massimo",
  ">": "più di",
  "<": "meno di",
};
const ORDER_LABELS: Record<string, string> = {
  name: "Titolo (A–Z)",
  score_desc: "Punteggio più alto",
  date_desc: "Più recenti",
  date_asc: "Più vecchi",
};

const FIELD_NAME: Record<string, string> = {
  developedBy: "Sviluppatore",
  publishedBy: "Publisher",
  hasGenre: "Genere",
  availableOn: "Piattaforma",
  belongsTo: "Serie",
  hasCharacter: "Personaggio",
  wonAward: "Premio",
  madeWith: "Motore di gioco",
  hasGameMode: "Modalità di gioco",
  metacriticScore: "Punteggio Metacritic",
  releaseYear: "Anno di uscita",
  releaseMonth: "Mese di uscita",
  gameName: "Titolo",
  countryOfOrigin: "Paese di origine",
  isA: "Categoria",
};
const FIELD_HINT: Record<string, string> = {
  developedBy: "es. FromSoftware",
  publishedBy: "es. Capcom",
  hasGenre: "es. action role-playing",
  availableOn: "es. Nintendo Switch",
  belongsTo: "es. The Legend of Zelda",
  hasCharacter: "es. Link",
  wonAward: "es. Game of the Year",
  madeWith: "es. Unreal Engine",
  hasGameMode: "es. co-op",
  metacriticScore: "da 0 a 100",
  releaseYear: "es. 2023",
  releaseMonth: "es. ottobre (di qualsiasi anno)",
  gameName: "parte del titolo",
  countryOfOrigin: "es. Japan",
  isA: "classi dedotte dal reasoner",
};
const GROUPS: { title: string; fields: string[] }[] = [
  { title: "Chi lo ha fatto", fields: ["developedBy", "publishedBy", "countryOfOrigin"] },
  { title: "Com'è fatto", fields: ["hasGenre", "hasGameMode", "belongsTo", "hasCharacter", "madeWith"] },
  { title: "Dove e quando", fields: ["availableOn", "releaseYear", "releaseMonth"] },
  { title: "Giudizi", fields: ["metacriticScore", "wonAward"] },
  { title: "Altro", fields: ["gameName", "isA"] },
];

/** Readable names for the inferred classes offered by the "Categoria" filter. */
const CLASS_LABELS: Record<string, string> = {
  AwardWinningGame: "Con almeno un premio",
  FranchiseGame: "Parte di una serie",
  SinglePlayerGame: "Giocatore singolo",
  MultiplayerGame: "Multiplayer",
  CoopGame: "Cooperativo",
  PCGame: "Per PC",
  ConsoleGame: "Per console",
  MobileGame: "Per mobile",
  NintendoGame: "Su piattaforme Nintendo",
  PlayStationGame: "Su PlayStation",
  XboxGame: "Su Xbox",
  HighlyRatedGame: "Molto recensito (≥ 85)",
  RecentGame: "Uscito dal 2020",
  SequelGame: "Sequel",
  StandaloneGame: "Non è un sequel",
  MultiConsoleGame: "Su 2+ console",
  NintendoPublishedGame: "Pubblicato da Nintendo",
  MultiPlatformGame: "Su 3+ piattaforme",
  WindowsGame: "Per Windows",
  MacOSGame: "Per macOS",
  LinuxGame: "Per Linux",
  AndroidGame: "Per Android",
  BrowserGame: "Nel browser",
  ArcadeGame: "Arcade",
  RetroComputerGame: "Home computer retro",
  VRGame: "Realtà virtuale",
  SonyPublishedGame: "Pubblicato da Sony",
  XboxPublishedGame: "Pubblicato da Xbox Game Studios",
  BandaiNamcoPublishedGame: "Pubblicato da Bandai Namco",
  SquareEnixPublishedGame: "Pubblicato da Square Enix",
  ElectronicArtsPublishedGame: "Pubblicato da Electronic Arts",
  KonamiPublishedGame: "Pubblicato da Konami",
  CapcomPublishedGame: "Pubblicato da Capcom",
  ActionGame: "Azione",
  RPGGame: "Gioco di ruolo",
  StrategyGame: "Strategia",
  SimulationGame: "Simulazione",
  AdventureGame: "Avventura",
  SportsGame: "Sportivo",
  RacingGame: "Corse",
  PuzzleGame: "Puzzle",
  HorrorGame: "Horror",
  PlatformerGame: "Platform",
  ShooterGame: "Sparatutto",
  CasualGame: "Casual",
  VisualNovelGame: "Visual novel",
  UnrealEngineGame: "Fatto con Unreal Engine",
  GOTYWinner: "Vincitore Game of the Year",
  JapaneseGame: "Giapponese",
  AmericanGame: "Statunitense",
};

/** One-click starting points. */
const PRESETS: { label: string; field: string; value: string }[] = [
  { label: "Molto recensiti", field: "isA", value: "HighlyRatedGame" },
  { label: "Usciti dal 2020", field: "isA", value: "RecentGame" },
  { label: "Giochi di ruolo", field: "isA", value: "RPGGame" },
  { label: "Cooperativi", field: "isA", value: "CoopGame" },
  { label: "Su più piattaforme", field: "isA", value: "MultiPlatformGame" },
  { label: "Vincitori Game of the Year", field: "isA", value: "GOTYWinner" },
];

const LIMITS = [25, 50, 100, 250, 500];
const MONTHS = [
  "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
  "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
];
const nameOf = (f: BuilderField) => FIELD_NAME[f.field] ?? f.label;

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
  const [collapsed, setCollapsed] = useState(false); // after a run the panel shrinks to one line
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
            value: kind === "number" || kind === "year" || kind === "month" ? Number(c.value) : c.value,
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

  const add = (f: BuilderField, value = "") => {
    setConds((c) => [
      ...c,
      { id: nextId++, field: f.field, op: f.ops[0], value, display: "" },
    ]);
    setMenu(false);
  };
  const patch = (id: number, p: Partial<Cond>) =>
    setConds((c) => c.map((x) => (x.id === id ? { ...x, ...p } : x)));
  const drop = (id: number) => setConds((c) => c.filter((x) => x.id !== id));

  if (schemaError)
    return <p className="text-sm text-brick">Impossibile caricare i filtri. Il backend è attivo?</p>;
  if (!schema) return <Loader2 className="h-4 w-4 animate-spin text-mute" />;

  const run = () => {
    onRun({ filters, order_by: orderBy, limit, output });
    setCollapsed(true);
  };
  const noMatch = count === 0;
  const fieldOptions = schema.fields.map((f) => ({ value: f.field, label: nameOf(f) }));
  const has = (field: string, value: string) => conds.some((c) => c.field === field && c.value === value);

  const valueInput = (c: Cond, f: BuilderField) => {
    if (f.kind === "entity")
      return (
        <div className="flex h-9 min-w-[200px] flex-1 items-center rounded-sm border border-rule bg-panel px-3 focus-within:border-mute">
          <SuggestInput
            value={c.display}
            types={[f.target!]}
            onChange={(v) => patch(c.id, { display: v, value: v })}
            onPick={(s) => patch(c.id, { value: s.uri, display: s.label })}
            placeholder={FIELD_HINT[f.field]}
            className="w-full bg-transparent text-sm placeholder:text-mute focus:outline-none"
          />
        </div>
      );
    if (f.kind === "month")
      return (
        <Dropdown
          className="min-w-[180px] flex-1"
          value={c.value}
          placeholder="Scegli un mese"
          options={MONTHS.map((m, i) => ({ value: String(i + 1), label: m }))}
          onChange={(v) => patch(c.id, { value: v })}
          ariaLabel="Mese"
        />
      );
    if (f.kind === "class")
      return (
        <Dropdown
          className="min-w-[220px] flex-1"
          value={c.value}
          searchable
          placeholder="Scegli una categoria"
          options={f.options!.map((o) => ({ value: o, label: CLASS_LABELS[o] ?? o }))}
          onChange={(v) => patch(c.id, { value: v })}
          ariaLabel="Categoria"
        />
      );
    return (
      <input
        type={f.kind === "text" ? "text" : "number"}
        value={c.value}
        onChange={(e) => patch(c.id, { value: e.target.value, display: e.target.value })}
        placeholder={FIELD_HINT[f.field]}
        className="h-9 min-w-[140px] flex-1 rounded-sm border border-rule bg-panel px-3 text-sm placeholder:text-mute focus:border-mute focus:outline-none"
      />
    );
  };

  if (collapsed) {
    const summary = conds
      .filter((c) => c.value.trim() !== "")
      .map((c) => {
        const f = field(c.field)!;
        const what = f.kind === "class" ? (CLASS_LABELS[c.value] ?? c.value) : c.display || c.value;
        return { id: c.id, text: `${nameOf(f)} ${OP_LABELS[c.op] ?? c.op} ${what}` };
      });
    return (
      <div className="flex min-h-11 flex-wrap items-center gap-2 rounded-sm border border-rule bg-panel/60 px-3 py-1.5">
        <span className="label mr-1">Filtri</span>
        {summary.length === 0 ? (
          <span className="text-sm text-mute">nessuno: tutti i giochi</span>
        ) : (
          summary.map((c) => (
            <span key={c.id} className="chip !py-1 !text-[13px]">
              {c.text}
            </span>
          ))
        )}
        <span className="ml-auto flex items-center gap-3">
          <span className="font-mono text-xs text-mute">
            {count === null ? "…" : `${count.toLocaleString("it-IT")} giochi`}
          </span>
          {loading ? (
            <button onClick={onCancel} className="btn h-8 !py-0">
              <X className="h-4 w-4" /> Annulla
            </button>
          ) : (
            <button onClick={() => setCollapsed(false)} className="btn h-8 !py-0">
              <SlidersHorizontal className="h-3.5 w-3.5" /> Modifica filtri
            </button>
          )}
        </span>
      </div>
    );
  }

  return (
    <div className="rounded-sm border border-rule bg-panel/60">
      <div className="flex flex-wrap items-baseline justify-between gap-2 px-4 pt-3.5">
        <h2 className="font-serif text-xl">Cerca videogiochi</h2>
        <span className="font-mono text-xs text-mute" aria-live="polite">
          {count === null ? (
            "conto…"
          ) : noMatch ? (
            <span className="text-brick">nessun gioco corrisponde</span>
          ) : (
            <>
              <b className="text-base font-medium text-ink">{count.toLocaleString("it-IT")}</b>{" "}
              {count === 1 ? "gioco corrisponde" : "giochi corrispondono"}
            </>
          )}
        </span>
      </div>

      <div className="space-y-2 px-4 py-3">
        {conds.length === 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="label mr-1">Parti da</span>
            {PRESETS.map((p) => (
              <button
                key={p.label}
                onClick={() => {
                  const f = field(p.field);
                  if (f && !has(p.field, p.value)) add(f, p.value);
                }}
                className="rounded-full border border-rule px-3 py-1 text-[13px] text-ink transition-colors hover:border-brick hover:text-brick"
              >
                {p.label}
              </button>
            ))}
          </div>
        )}

        {conds.map((c, i) => {
          const f = field(c.field)!;
          const opOptions = f.ops.map((op) => ({ value: op, label: OP_LABELS[op] ?? op }));
          return (
            <div key={c.id} className="flex flex-wrap items-center gap-2 animate-fade-in">
              <span className="label w-9 flex-shrink-0">{i === 0 ? "dove" : "e"}</span>
              <Dropdown
                className="w-44 flex-shrink-0"
                value={c.field}
                options={fieldOptions}
                ariaLabel="Campo"
                onChange={(name) => {
                  const nf = field(name)!;
                  patch(c.id, { field: nf.field, op: nf.ops[0], value: "", display: "" });
                }}
              />
              {f.ops.length === 2 && (f.kind === "entity" || f.kind === "class") ? (
                <div className="inline-flex h-9 flex-shrink-0 rounded-sm border border-rule p-0.5" role="group" aria-label="Operatore">
                  {opOptions.map((o) => (
                    <button
                      key={o.value}
                      onClick={() => patch(c.id, { op: o.value })}
                      className={`rounded-[3px] px-3 text-sm transition-colors ${
                        c.op === o.value
                          ? o.value === "is_not"
                            ? "bg-brick text-paper"
                            : "bg-ink text-paper"
                          : "text-mute hover:text-ink"
                      }`}
                    >
                      {o.label}
                    </button>
                  ))}
                </div>
              ) : f.ops.length === 1 ? (
                <span className="w-12 flex-shrink-0 px-1 text-sm text-mute">è</span>
              ) : (
                <Dropdown
                  className="w-32 flex-shrink-0"
                  value={c.op}
                  options={opOptions}
                  ariaLabel="Operatore"
                  onChange={(op) => patch(c.id, { op })}
                />
              )}
              {valueInput(c, f)}
              <button
                onClick={() => drop(c.id)}
                className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-sm text-mute hover:bg-raised hover:text-ink"
                aria-label="Rimuovi filtro"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}

        <div className="relative inline-block" ref={menuRef}>
          <button
            onClick={() => setMenu((m) => !m)}
            className="inline-flex h-9 items-center gap-1.5 rounded-sm border border-dashed border-rule px-3 text-sm text-mute transition-colors hover:border-brick hover:text-ink"
            aria-expanded={menu}
          >
            <Plus className="h-3.5 w-3.5" /> {conds.length ? "Aggiungi un altro filtro" : "Aggiungi un filtro"}
          </button>
          {menu && (
            <div className="absolute left-0 top-full z-50 mt-1.5 grid w-[min(760px,92vw)] animate-fade-in grid-cols-1 gap-x-6 gap-y-3 rounded-sm border border-rule bg-panel p-4 shadow-[0_16px_40px_-8px_rgba(0,0,0,0.7)] sm:grid-cols-3">
              {GROUPS.map((g) => (
                <div key={g.title}>
                  <p className="label mb-1">{g.title}</p>
                  <ul>
                    {g.fields
                      .map((name) => field(name))
                      .filter((f): f is BuilderField => !!f)
                      .map((f) => (
                        <li key={f.field}>
                          <button
                            onClick={() => add(f)}
                            className="w-full rounded-sm px-2 py-1.5 text-left hover:bg-raised"
                          >
                            <span className="block text-sm">{nameOf(f)}</span>
                            <span className="block text-[11px] text-mute">{FIELD_HINT[f.field]}</span>
                          </button>
                        </li>
                      ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-5 gap-y-2.5 border-t border-rule px-4 py-3">
        <label className="flex items-center gap-2 text-[13px] text-mute">
          Ordina per
          <Dropdown
            className="w-44"
            value={orderBy}
            options={schema.orders.map((o) => ({ value: o, label: ORDER_LABELS[o] ?? o }))}
            onChange={setOrderBy}
            ariaLabel="Ordinamento"
          />
        </label>
        <label className="flex items-center gap-2 text-[13px] text-mute">
          Mostra al massimo
          <Dropdown
            className="w-20"
            value={String(limit)}
            options={LIMITS.map((n) => ({ value: String(n), label: String(n) }))}
            onChange={(v) => setLimit(Number(v))}
            ariaLabel="Numero massimo di risultati"
          />
        </label>
        <div className="flex items-center gap-2 text-[13px] text-mute">
          Come
          <div className="inline-flex h-9 rounded-sm border border-rule p-0.5" role="group" aria-label="Formato dei risultati">
            {(
              [
                ["table", "Elenco", List],
                ["graph", "Relazioni", Network],
              ] as const
            ).map(([v, label, Icon]) => (
              <button
                key={v}
                onClick={() => setOutput(v)}
                className={`inline-flex items-center gap-1.5 rounded-[3px] px-3 text-sm transition-colors ${
                  output === v ? "bg-raised text-ink" : "text-mute hover:text-ink"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </button>
            ))}
          </div>
        </div>
        <span className="ml-auto">
          {loading ? (
            <button onClick={onCancel} className="btn h-9">
              <X className="h-4 w-4" /> Annulla
            </button>
          ) : (
            <button onClick={run} disabled={noMatch} className="btn btn-primary h-9">
              Mostra i risultati <ArrowRight className="h-4 w-4" />
            </button>
          )}
        </span>
      </div>
    </div>
  );
}
