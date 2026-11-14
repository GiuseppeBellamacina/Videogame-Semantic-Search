import { useEffect, useState, useMemo } from "react";
import { X, ChevronDown, ExternalLink, RefreshCw } from "lucide-react";
import type { NodeDetails, GraphData, GraphNode } from "@/types";
import { getNodeDetails } from "@/lib/api";
import { Thumb } from "@/components/Thumb";
import { IMAGE_TYPES, typeColor, typeLabel, typeSize } from "@/lib/theme";
import { retryImage } from "@/lib/imageQueue";

interface NodeDetailProps {
  uri: string | null;
  onClose: () => void;
  onNavigate: (uri: string) => void;
  onGraphExpand?: (graph: GraphData) => void;
}

const makeNode = (uri: string, label: string, type: string): GraphNode => ({
  id: uri,
  label,
  type,
  color: typeColor(type),
  size: typeSize(type),
});

const PREVIEW = 4;
type Rel = { predicate: string; uri: string; label: string; type: string };

function group(rels: Rel[]) {
  const m = new Map<string, Rel[]>();
  for (const r of rels) m.set(r.predicate, [...(m.get(r.predicate) ?? []), r]);
  return [...m.entries()];
}

/** "God of War" alone lands on a disambiguation page: add the year and "video game" for games. */
function wikiQuery(d: { type: string; label: string; properties: Record<string, string> }) {
  if (d.type !== "VideoGame") return d.label;
  const date = Object.entries(d.properties).find(([k]) => /release/i.test(k))?.[1] ?? "";
  return `${d.label} ${date.slice(0, 4)} video game`.replace(/\s+/g, " ");
}

export function NodeDetail({ uri, onClose, onNavigate, onGraphExpand }: NodeDetailProps) {
  const [details, setDetails] = useState<NodeDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<Set<string>>(new Set());
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    if (!uri) {
      setDetails(null);
      return;
    }
    setLoading(true);
    setError(null);
    setOpen(new Set());
    getNodeDetails(uri)
      .then((r) => setDetails(r.details))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [uri]);

  const outgoing = useMemo(
    () =>
      group(
        (details?.outgoing_relations ?? []).map((r) => ({
          predicate: r.predicate,
          uri: r.target_uri,
          label: r.target_label,
          type: r.target_type,
        })),
      ),
    [details],
  );
  const incoming = useMemo(
    () =>
      group(
        (details?.incoming_relations ?? []).map((r) => ({
          predicate: r.predicate,
          uri: r.source_uri,
          label: r.source_label,
          type: r.source_type,
        })),
      ),
    [details],
  );

  if (!uri) return null;

  const toggle = (k: string) =>
    setOpen((p) => {
      const n = new Set(p);
      if (n.has(k)) n.delete(k);
      else n.add(k);
      return n;
    });

  const follow = (r: Rel, dir: "out" | "in") => {
    onNavigate(r.uri);
    if (!onGraphExpand || !details) return;
    onGraphExpand({
      nodes: [makeNode(uri, details.label, details.type), makeNode(r.uri, r.label, r.type)],
      links: [
        dir === "out"
          ? { source: uri, target: r.uri, label: r.predicate }
          : { source: r.uri, target: uri, label: r.predicate },
      ],
    });
  };

  const renderGroups = (title: string, groups: [string, Rel[]][], dir: "out" | "in", total: number) =>
    groups.length > 0 && (
      <section>
        <h3 className="label mb-1">
          {title} <span className="text-mute">· {total}</span>
        </h3>
        <ul className="rule-y">
          {groups.map(([pred, items]) => {
            const key = `${dir}:${pred}`;
            const isOpen = open.has(key);
            const shown = isOpen ? items : items.slice(0, PREVIEW);
            return (
              <li key={key} className="py-2.5">
                <button
                  onClick={() => toggle(key)}
                  className="flex w-full items-center gap-2 text-left"
                  aria-expanded={isOpen}
                >
                  <span className="flex-1 font-mono text-xs text-petrol">{pred}</span>
                  <span className="font-mono text-[11px] text-mute">{items.length}</span>
                  <ChevronDown
                    className={`h-3 w-3 text-mute transition-transform ${isOpen ? "" : "-rotate-90"}`}
                  />
                </button>
                <ul className="mt-1.5 space-y-0.5">
                  {shown.map((r, i) => (
                    <li key={i}>
                      <button
                        onClick={() => follow(r, dir)}
                        className="flex w-full items-center gap-2.5 rounded-sm px-1 py-1 text-left hover:bg-raised"
                      >
                        <Thumb type={r.type} name={r.label} size={26} />
                        <span className="flex-1 truncate text-sm">{r.label}</span>
                        <span className="label">{typeLabel(r.type)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
                {!isOpen && items.length > PREVIEW && (
                  <button
                    onClick={() => toggle(key)}
                    className="mt-1 px-1 text-xs text-mute hover:text-ink"
                  >
                    altri {items.length - PREVIEW}…
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      </section>
    );

  const showType = details && details.type && details.type !== "Unknown" && details.type !== "Thing";

  return (
    <aside data-detail className="fixed inset-y-0 right-0 z-50 w-full overflow-y-auto border-l border-rule bg-panel shadow-[-24px_0_48px_-24px_rgba(0,0,0,0.7)] animate-slide-in sm:w-[26rem]">
      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-rule bg-panel px-5 py-3">
        <span className="label">{showType ? typeLabel(details!.type) : "Dettaglio"}</span>
        <button onClick={onClose} className="rounded-sm p-1 text-mute hover:bg-raised hover:text-ink" aria-label="Chiudi">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="space-y-7 px-5 py-6">
        {loading && (
          <div className="space-y-3" aria-label="Carico">
            <div className="h-24 w-24 animate-shimmer rounded-sm bg-raised" />
            <div className="h-6 w-2/3 animate-shimmer rounded-sm bg-raised" />
            <div className="h-3 w-1/3 animate-shimmer rounded-sm bg-raised" />
          </div>
        )}
        {error && <p className="border-l-2 border-brick pl-3 text-sm">{error}</p>}

        {details && !loading && (
          <>
            <header className="flex items-end gap-4">
              <Thumb type={details.type} name={details.label} size={112} urgent />
              <div className="min-w-0 pb-1">
                <h2 className="font-serif text-[28px] leading-[1.1]">{details.label}</h2>
                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1">
                  <a
                    href={`https://en.wikipedia.org/wiki/Special:Search?search=${encodeURIComponent(wikiQuery(details))}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-mute hover:text-brick"
                  >
                    Cerca su Wikipedia <ExternalLink className="h-3 w-3" />
                  </a>
                  {IMAGE_TYPES.has(details.type) && (
                    <button
                      onClick={async () => {
                        setRetrying(true);
                        await retryImage(details.type, details.label);
                        setRetrying(false);
                      }}
                      disabled={retrying}
                      title="Cerca un'altra immagine su Wikipedia"
                      className="inline-flex items-center gap-1 text-xs text-mute hover:text-brick disabled:opacity-50"
                    >
                      <RefreshCw className={`h-3 w-3 ${retrying ? "animate-spin" : ""}`} />
                      Riprova copertina
                    </button>
                  )}
                </div>
              </div>
            </header>

            {Object.keys(details.properties).length > 0 && (
              <section>
                <h3 className="label mb-1">Proprietà</h3>
                <dl className="rule-y">
                  {Object.entries(details.properties).map(([k, v]) => (
                    <div key={k} className="grid grid-cols-[7rem_1fr] gap-3 py-2">
                      <dt className="font-mono text-[11px] text-mute">{k}</dt>
                      <dd className="break-words text-sm">{v.length > 300 ? `${v.slice(0, 300)}…` : v}</dd>
                    </div>
                  ))}
                </dl>
              </section>
            )}

            {renderGroups("In uscita", outgoing, "out", details.outgoing_relations.length)}
            {renderGroups(
              "In entrata",
              incoming,
              "in",
              details.truncated && details.total_incoming ? details.total_incoming : details.incoming_relations.length,
            )}
            {details.truncated && (
              <p className="text-xs text-mute">
                Mostro le prime {details.incoming_relations.length} relazioni in entrata.
              </p>
            )}
          </>
        )}
      </div>
    </aside>
  );
}
