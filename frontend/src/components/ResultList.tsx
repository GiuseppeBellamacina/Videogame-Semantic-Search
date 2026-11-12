import { useMemo, useState } from "react";
import type { GraphNode, QueryResult } from "@/types";
import { Thumb } from "@/components/Thumb";
import { typeLabel } from "@/lib/theme";

interface ResultListProps {
  results: QueryResult[];
  totalRows: number;
  nodes: GraphNode[];
  onNodeClick: (uri: string) => void;
}

const VG = "http://www.videogame-ontology.org/";
const PAGE = 60;

const isUri = (v: string | null): v is string => !!v && v.startsWith(VG);

function localName(uri: string): string {
  const frag = uri.split("#").pop() || uri;
  return decodeURIComponent(frag.split("/").pop() || frag).replace(/_/g, " ");
}

export function ResultList({ results, totalRows, nodes, onNodeClick }: ResultListProps) {
  const [shown, setShown] = useState(PAGE);
  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  if (!results.length) {
    return (
      <div className="py-10">
        <p className="font-serif text-xl">Nessun risultato</p>
        <p className="mt-1 text-sm text-mute">
          Prova a riformulare la domanda o ad allargare i filtri.
        </p>
      </div>
    );
  }

  const info = (uri: string) => {
    const n = byId.get(uri);
    return { label: n?.label ?? localName(uri), type: n?.type ?? "Unknown" };
  };
  const isTriples = ["subject", "predicate", "object"].every((k) => k in results[0]);

  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <h3 className="label">Risultati</h3>
        <span className="font-mono text-xs text-mute">{totalRows}</span>
      </div>
      <ul className="rule-y">
        {results.slice(0, shown).map((row, i) => {
          const uris = Object.entries(row).filter(([, v]) => isUri(v)) as [string, string][];
          if (isTriples) {
            const s = info(row.subject as string);
            const o = isUri(row.object) ? info(row.object) : null;
            return (
              <li key={i} className="flex items-center gap-3 py-2.5">
                <Thumb type={s.type} name={s.label} size={34} />
                <div className="min-w-0 text-sm leading-snug">
                  <button
                    className="text-left hover:text-brick"
                    onClick={() => onNodeClick(row.subject as string)}
                  >
                    {s.label}
                  </button>
                  <span className="mx-1.5 font-mono text-[11px] text-mute">{row.predicate}</span>
                  {o ? (
                    <button
                      className="text-left hover:text-brick"
                      onClick={() => onNodeClick(row.object as string)}
                    >
                      {o.label}
                    </button>
                  ) : (
                    <span className="text-mute">{row.object}</span>
                  )}
                </div>
              </li>
            );
          }

          // main entity: prefer a video game, else the first entity in the row
          const main =
            uris.find(([, u]) => info(u).type === "VideoGame") ?? uris[0];
          const mainInfo = main ? info(main[1]) : null;
          const others = uris.filter(([k]) => k !== main?.[0]);
          const meta = Object.entries(row).filter(
            ([, v]) => v && !isUri(v) && v !== mainInfo?.label,
          );
          return (
            <li key={i} className="flex gap-3 py-3">
              {mainInfo && <Thumb type={mainInfo.type} name={mainInfo.label} size={52} />}
              <div className="min-w-0 flex-1">
                {main ? (
                  <button
                    className="text-left font-serif text-[17px] leading-tight hover:text-brick"
                    onClick={() => onNodeClick(main[1])}
                  >
                    {mainInfo!.label}
                  </button>
                ) : (
                  <span className="font-serif text-[17px]">{Object.values(row)[0]}</span>
                )}
                {mainInfo && (
                  <span className="label ml-2 align-middle">{typeLabel(mainInfo.type)}</span>
                )}
                {others.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {others.map(([k, u]) => (
                      <button key={k} className="chip hover:border-mute" onClick={() => onNodeClick(u)}>
                        {info(u).label}
                      </button>
                    ))}
                  </div>
                )}
                {meta.length > 0 && (
                  <p className="mt-1 font-mono text-[11px] text-mute">
                    {meta.map(([k, v]) => `${k.replace(/Name$/, "")} ${v}`).join(" · ")}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ul>
      {shown < results.length && (
        <button className="btn mt-3 w-full" onClick={() => setShown((s) => s + PAGE)}>
          Mostra altri {Math.min(PAGE, results.length - shown)}
        </button>
      )}
    </div>
  );
}
