import { useEffect, useState } from "react";
import { Loader2, Plus, Play, Trash2, X } from "lucide-react";
import { getBuilderSchema } from "@/lib/api";
import { SuggestInput } from "@/components/SuggestInput";
import type {
  BuilderField,
  BuilderRequest,
  BuilderSchema,
} from "@/types";

interface Row {
  id: number;
  field: string;
  op: string;
  value: string; // URI (picked suggestion), number or free text
  display: string; // what the input shows
}

const ORDER_LABELS: Record<string, string> = {
  name: "Titolo (A-Z)",
  score_desc: "Metacritic (alto → basso)",
  date_desc: "Data di uscita (recenti prima)",
  date_asc: "Data di uscita (vecchi prima)",
};
const OP_LABELS: Record<string, string> = {
  is: "è",
  is_not: "non è",
  contains: "contiene",
  equals: "uguale a",
};

const selectCls =
  "bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500";
const inputCls = `${selectCls} w-full placeholder-gray-500`;

interface QueryBuilderProps {
  onRun: (body: BuilderRequest) => void;
  onCancel: () => void;
  loading: boolean;
}

export function QueryBuilder({ onRun, onCancel, loading }: QueryBuilderProps) {
  const [schema, setSchema] = useState<BuilderSchema | null>(null);
  const [schemaError, setSchemaError] = useState(false);
  const [rows, setRows] = useState<Row[]>([]);
  const [orderBy, setOrderBy] = useState("name");
  const [limit, setLimit] = useState(50);

  useEffect(() => {
    getBuilderSchema().then(setSchema).catch(() => setSchemaError(true));
  }, []);

  const fieldOf = (name: string): BuilderField | undefined =>
    schema?.fields.find((f) => f.field === name);

  const addRow = () => {
    const first = schema?.fields[0];
    if (!first) return;
    setRows((r) => [
      ...r,
      { id: Date.now() + r.length, field: first.field, op: first.ops[0], value: "", display: "" },
    ]);
  };
  const update = (id: number, patch: Partial<Row>) =>
    setRows((r) => r.map((x) => (x.id === id ? { ...x, ...patch } : x)));

  const changeField = (id: number, name: string) => {
    const f = fieldOf(name);
    if (f) update(id, { field: name, op: f.ops[0], value: f.kind === "class" ? f.options![0] : "", display: "" });
  };

  const run = () => {
    const filters = rows
      .filter((r) => r.value.toString().trim() !== "")
      .map((r) => {
        const kind = fieldOf(r.field)?.kind;
        return {
          field: r.field,
          op: r.op,
          value: kind === "number" || kind === "year" ? Number(r.value) : r.value,
        };
      });
    onRun({ filters, order_by: orderBy, limit });
  };

  if (schemaError) {
    return <p className="text-sm text-red-400">Impossibile caricare lo schema del builder.</p>;
  }
  if (!schema) {
    return <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />;
  }

  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-4 space-y-3">
      <p className="text-sm text-gray-400">
        Cerca <span className="text-white font-medium">videogiochi</span> che soddisfano tutti i filtri:
      </p>

      {rows.map((row) => {
        const f = fieldOf(row.field)!;
        return (
          <div key={row.id} className="flex flex-col sm:flex-row gap-2 sm:items-start">
            <select
              value={row.field}
              onChange={(e) => changeField(row.id, e.target.value)}
              className={`${selectCls} sm:w-48`}
            >
              {schema.fields.map((x) => (
                <option key={x.field} value={x.field}>
                  {x.label}
                </option>
              ))}
            </select>
            <select
              value={row.op}
              onChange={(e) => update(row.id, { op: e.target.value })}
              className={`${selectCls} sm:w-32`}
            >
              {f.ops.map((op) => (
                <option key={op} value={op}>
                  {OP_LABELS[op] ?? op}
                </option>
              ))}
            </select>

            <div className="flex-1 min-w-0">
              {f.kind === "entity" ? (
                <SuggestInput
                  value={row.display}
                  types={[f.target!]}
                  onChange={(v) => update(row.id, { display: v, value: v })}
                  onPick={(s) => update(row.id, { value: s.uri, display: s.label })}
                  placeholder={`Scrivi per cercare: ${f.label.toLowerCase()}...`}
                  className={inputCls}
                />
              ) : f.kind === "class" ? (
                <select
                  value={row.value}
                  onChange={(e) => update(row.id, { value: e.target.value })}
                  className={inputCls}
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
                  value={row.value}
                  onChange={(e) => update(row.id, { value: e.target.value, display: e.target.value })}
                  placeholder={f.kind === "year" ? "es. 2023" : f.kind === "number" ? "es. 85" : ""}
                  className={inputCls}
                />
              )}
            </div>

            <button
              type="button"
              onClick={() => setRows((r) => r.filter((x) => x.id !== row.id))}
              className="p-2 text-gray-500 hover:text-red-400 transition-colors self-end sm:self-auto"
              aria-label="Rimuovi filtro"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        );
      })}

      <div className="flex flex-wrap items-center gap-3 pt-1">
        <button
          type="button"
          onClick={addRow}
          className="flex items-center gap-1.5 px-3 py-2 text-sm text-indigo-300 hover:text-white bg-indigo-600/10 hover:bg-indigo-600/30 rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" /> Aggiungi filtro
        </button>
        <select value={orderBy} onChange={(e) => setOrderBy(e.target.value)} className={selectCls}>
          {schema.orders.map((o) => (
            <option key={o} value={o}>
              {ORDER_LABELS[o] ?? o}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-400">
          Max
          <input
            type="number"
            min={1}
            max={500}
            value={limit}
            onChange={(e) => setLimit(Math.max(1, Math.min(500, Number(e.target.value) || 1)))}
            className={`${selectCls} w-20`}
          />
        </label>
        <div className="ml-auto">
          {loading ? (
            <button
              type="button"
              onClick={onCancel}
              className="px-5 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg font-medium flex items-center gap-2"
            >
              <X className="w-4 h-4" /> Annulla
            </button>
          ) : (
            <button
              type="button"
              onClick={run}
              className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium flex items-center gap-2"
            >
              <Play className="w-4 h-4" /> Esegui
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
