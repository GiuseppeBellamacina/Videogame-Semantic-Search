import { useEffect, useMemo, useRef, useState } from "react";
import { X, Loader2, ArrowRight, ArrowLeft, GitFork } from "lucide-react";
import { getNodeDetails } from "@/lib/api";
import type { GraphNode, GraphData, NodeDetails } from "@/types";

const NODE_COLORS: Record<string, string> = {
  VideoGame: "#6366f1",
  Developer: "#f59e0b",
  Publisher: "#10b981",
  Genre: "#ef4444",
  Platform: "#3b82f6",
  Character: "#ec4899",
  Franchise: "#8b5cf6",
  Award: "#f97316",
  GameEngine: "#14b8a6",
  Unknown: "#6b7280",
};

interface NodeContextMenuProps {
  node: GraphNode;
  x: number;
  y: number;
  maxResults: number;
  onNavigate: (uri: string) => void;
  onGraphExpand: (graph: GraphData) => void;
  onClose: () => void;
}

function makeNode(uri: string, label: string, type: string): GraphNode {
  return {
    id: uri,
    label,
    type,
    color: NODE_COLORS[type] ?? NODE_COLORS.Unknown,
    size: 8,
  };
}

export function NodeContextMenu({
  node,
  x,
  y,
  maxResults,
  onNavigate,
  onGraphExpand,
  onClose,
}: NodeContextMenuProps) {
  const [details, setDetails] = useState<NodeDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "outgoing" | "incoming">("all");
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getNodeDetails(node.id)
      .then((res) => setDetails(res.details))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [node.id]);

  // Close on outside click or Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node))
        onClose();
    };
    document.addEventListener("keydown", handleKey);
    document.addEventListener("mousedown", handleClick);
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.removeEventListener("mousedown", handleClick);
    };
  }, [onClose]);

  // Adjust position to stay within viewport
  const style: React.CSSProperties = {
    position: "fixed",
    top: Math.min(y, window.innerHeight - 400),
    left: Math.min(x, window.innerWidth - 320),
    zIndex: 1000,
  };

  const allOutgoing = details?.outgoing_relations ?? [];
  const allIncoming = details?.incoming_relations ?? [];
  const outgoingTotal = allOutgoing.length;
  const incomingTotal = allIncoming.length;

  // Sliced lists respecting maxResults
  const outgoing = allOutgoing.slice(0, maxResults);
  const incoming = allIncoming.slice(0, maxResults);

  const shownOut = filter === "incoming" ? [] : outgoing;
  const shownIn = filter === "outgoing" ? [] : incoming;

  // Count unique nodes that "expand all" would add
  const expandAllCount = useMemo(() => {
    const uris = new Set<string>();
    for (const r of allOutgoing) uris.add(r.target_uri);
    for (const r of allIncoming) uris.add(r.source_uri);
    uris.delete(node.id);
    return uris.size;
  }, [allOutgoing, allIncoming, node.id]);

  // Count unique nodes visible in current filter view
  const expandFilteredCount = useMemo(() => {
    const uris = new Set<string>();
    if (filter !== "incoming") for (const r of outgoing) uris.add(r.target_uri);
    if (filter !== "outgoing") for (const r of incoming) uris.add(r.source_uri);
    uris.delete(node.id);
    return uris.size;
  }, [filter, outgoing, incoming, node.id]);

  function expandSingle(
    targetUri: string,
    targetLabel: string,
    targetType: string,
    predicate: string,
    direction: "out" | "in",
  ) {
    const newNode = makeNode(targetUri, targetLabel, targetType);
    const newLink =
      direction === "out"
        ? { source: node.id, target: targetUri, label: predicate }
        : { source: targetUri, target: node.id, label: predicate };
    onGraphExpand({ nodes: [newNode], links: [newLink] });
    onClose();
  }

  function expandFiltered() {
    const nodes: GraphNode[] = [];
    const links: { source: string; target: string; label: string }[] = [];
    const seenUris = new Set<string>();
    if (filter !== "incoming") {
      for (const r of outgoing) {
        if (!seenUris.has(r.target_uri)) {
          nodes.push(makeNode(r.target_uri, r.target_label, r.target_type));
          seenUris.add(r.target_uri);
        }
        links.push({ source: node.id, target: r.target_uri, label: r.predicate });
      }
    }
    if (filter !== "outgoing") {
      for (const r of incoming) {
        if (!seenUris.has(r.source_uri)) {
          nodes.push(makeNode(r.source_uri, r.source_label, r.source_type));
          seenUris.add(r.source_uri);
        }
        links.push({ source: r.source_uri, target: node.id, label: r.predicate });
      }
    }
    onGraphExpand({ nodes, links });
    onClose();
  }

  function expandAll() {
    const nodes: GraphNode[] = [];
    const links: { source: string; target: string; label: string }[] = [];
    const seenUris = new Set<string>();
    for (const r of allOutgoing) {
      if (!seenUris.has(r.target_uri)) {
        nodes.push(makeNode(r.target_uri, r.target_label, r.target_type));
        seenUris.add(r.target_uri);
      }
      links.push({ source: node.id, target: r.target_uri, label: r.predicate });
    }
    for (const r of allIncoming) {
      if (!seenUris.has(r.source_uri)) {
        nodes.push(makeNode(r.source_uri, r.source_label, r.source_type));
        seenUris.add(r.source_uri);
      }
      links.push({ source: r.source_uri, target: node.id, label: r.predicate });
    }
    onGraphExpand({ nodes, links });
    onClose();
  }

  return (
    <div
      ref={menuRef}
      style={style}
      className="w-80 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl overflow-hidden animate-fade-in"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-gray-900/95">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-white truncate">{node.label}</p>
          <p className="text-xs text-gray-500">{node.type}</p>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-800 rounded-lg transition-colors flex-shrink-0 ml-2"
        >
          <X className="w-4 h-4 text-gray-400" />
        </button>
      </div>

      {/* Open in sidebar */}
      <div className="px-4 py-2 border-b border-gray-800">
        <button
          onClick={() => { onNavigate(node.id); onClose(); }}
          className="w-full text-xs text-indigo-400 hover:text-indigo-300 text-left transition-colors"
        >
          Apri nella sidebar →
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex border-b border-gray-800">
        {(["all", "outgoing", "incoming"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            className={`flex-1 py-2 text-xs font-medium transition-colors ${
              filter === t
                ? "text-indigo-400 border-b-2 border-indigo-400"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {t === "all"
              ? "Tutte"
              : t === "outgoing"
                ? `→ Uscenti (${outgoingTotal})`
                : `← Entranti (${incomingTotal})`}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="max-h-56 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center py-8 text-gray-500">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            <span className="text-sm">Caricamento relazioni...</span>
          </div>
        )}

        {error && <div className="px-4 py-3 text-sm text-red-400">{error}</div>}

        {details && (
          <div className="divide-y divide-gray-800/60">
            {/* Outgoing */}
            {shownOut.length > 0 && (
              <div>
                {filter === "all" && (
                  <p className="px-4 py-1.5 text-[10px] text-gray-500 uppercase tracking-wide bg-gray-800/30">
                    Uscenti
                  </p>
                )}
                {shownOut.map((rel, i) => (
                  <button
                    key={i}
                    onClick={() =>
                      expandSingle(rel.target_uri, rel.target_label, rel.target_type, rel.predicate, "out")
                    }
                    className="w-full px-4 py-2.5 flex items-start gap-2 hover:bg-gray-800 transition-colors text-left"
                  >
                    <ArrowRight className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0 mt-0.5" />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs text-gray-300 truncate">{rel.target_label}</p>
                      <p className="text-[10px] text-gray-500">{rel.predicate} · {rel.target_type}</p>
                    </div>
                    <span className="text-[10px] text-indigo-500 flex-shrink-0 mt-0.5 font-mono">+1</span>
                  </button>
                ))}
                {outgoingTotal > maxResults && filter !== "incoming" && (
                  <p className="px-4 py-1.5 text-[10px] text-gray-600 italic">
                    +{outgoingTotal - maxResults} relazioni non mostrate (aumenta il limite)
                  </p>
                )}
              </div>
            )}

            {/* Incoming */}
            {shownIn.length > 0 && (
              <div>
                {filter === "all" && (
                  <p className="px-4 py-1.5 text-[10px] text-gray-500 uppercase tracking-wide bg-gray-800/30">
                    Entranti
                  </p>
                )}
                {shownIn.map((rel, i) => (
                  <button
                    key={i}
                    onClick={() =>
                      expandSingle(rel.source_uri, rel.source_label, rel.source_type, rel.predicate, "in")
                    }
                    className="w-full px-4 py-2.5 flex items-start gap-2 hover:bg-gray-800 transition-colors text-left"
                  >
                    <ArrowLeft className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs text-gray-300 truncate">{rel.source_label}</p>
                      <p className="text-[10px] text-gray-500">{rel.predicate} · {rel.source_type}</p>
                    </div>
                    <span className="text-[10px] text-emerald-600 flex-shrink-0 mt-0.5 font-mono">+1</span>
                  </button>
                ))}
                {incomingTotal > maxResults && filter !== "outgoing" && (
                  <p className="px-4 py-1.5 text-[10px] text-gray-600 italic">
                    +{incomingTotal - maxResults} relazioni non mostrate (aumenta il limite)
                  </p>
                )}
              </div>
            )}

            {!loading && shownOut.length === 0 && shownIn.length === 0 && (
              <p className="px-4 py-6 text-sm text-gray-600 text-center">
                Nessuna relazione trovata
              </p>
            )}
          </div>
        )}
      </div>

      {/* Footer expand actions */}
      {details && (expandFilteredCount > 0 || expandAllCount > 0) && (
        <div className="border-t border-gray-800 p-3 space-y-2">
          {expandFilteredCount > 0 && (
            <button
              onClick={expandFiltered}
              className="w-full flex items-center gap-2 px-3 py-2 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 text-xs rounded-lg transition-colors"
            >
              <GitFork className="w-3.5 h-3.5 flex-shrink-0" />
              <span>
                Espandi{" "}
                {filter === "all"
                  ? "visibili"
                  : filter === "outgoing"
                    ? "uscenti"
                    : "entranti"}{" "}
                nel grafo
              </span>
              <span className="ml-auto font-semibold">+{expandFilteredCount} nodi</span>
            </button>
          )}
          {expandAllCount > expandFilteredCount && (
            <button
              onClick={expandAll}
              className="w-full flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs rounded-lg transition-colors"
            >
              <GitFork className="w-3.5 h-3.5 flex-shrink-0" />
              <span>Espandi tutti nel grafo</span>
              <span className="ml-auto font-semibold">+{expandAllCount} nodi</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
          <p className="text-xs text-gray-500">{node.type}</p>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-800 rounded-lg transition-colors flex-shrink-0 ml-2"
        >
          <X className="w-4 h-4 text-gray-400" />
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex border-b border-gray-800">
        {(["all", "outgoing", "incoming"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            className={`flex-1 py-2 text-xs font-medium transition-colors ${
              filter === t
                ? "text-indigo-400 border-b-2 border-indigo-400"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {t === "all"
              ? "Tutte"
              : t === "outgoing"
                ? `→ Uscenti (${outgoingTotal})`
                : `← Entranti (${incomingTotal})`}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="max-h-72 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center py-8 text-gray-500">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            <span className="text-sm">Caricamento relazioni...</span>
          </div>
        )}

        {error && <div className="px-4 py-3 text-sm text-red-400">{error}</div>}

        {details && (
          <div className="divide-y divide-gray-800/60">
            {/* Outgoing */}
            {shownOut.length > 0 && (
              <div>
                {filter === "all" && (
                  <p className="px-4 py-1.5 text-[10px] text-gray-500 uppercase tracking-wide bg-gray-800/30">
                    Uscenti
                  </p>
                )}
                {shownOut.map((rel, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      onNavigate(rel.target_uri);
                      onClose();
                    }}
                    className="w-full px-4 py-2.5 flex items-start gap-2 hover:bg-gray-800 transition-colors text-left"
                  >
                    <ArrowRight className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0 mt-0.5" />
                    <div className="min-w-0">
                      <p className="text-xs text-gray-300 truncate">
                        {rel.target_label}
                      </p>
                      <p className="text-[10px] text-gray-500">
                        {rel.predicate} · {rel.target_type}
                      </p>
                    </div>
                  </button>
                ))}
                {outgoingTotal > maxResults && filter !== "incoming" && (
                  <p className="px-4 py-1.5 text-[10px] text-gray-600 italic">
                    +{outgoingTotal - maxResults} relazioni non mostrate
                  </p>
                )}
              </div>
            )}

            {/* Incoming */}
            {shownIn.length > 0 && (
              <div>
                {filter === "all" && (
                  <p className="px-4 py-1.5 text-[10px] text-gray-500 uppercase tracking-wide bg-gray-800/30">
                    Entranti
                  </p>
                )}
                {shownIn.map((rel, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      onNavigate(rel.source_uri);
                      onClose();
                    }}
                    className="w-full px-4 py-2.5 flex items-start gap-2 hover:bg-gray-800 transition-colors text-left"
                  >
                    <ArrowLeft className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <div className="min-w-0">
                      <p className="text-xs text-gray-300 truncate">
                        {rel.source_label}
                      </p>
                      <p className="text-[10px] text-gray-500">
                        {rel.predicate} · {rel.source_type}
                      </p>
                    </div>
                  </button>
                ))}
                {incomingTotal > maxResults && filter !== "outgoing" && (
                  <p className="px-4 py-1.5 text-[10px] text-gray-600 italic">
                    +{incomingTotal - maxResults} relazioni non mostrate
                  </p>
                )}
              </div>
            )}

            {!loading && shownOut.length === 0 && shownIn.length === 0 && (
              <p className="px-4 py-6 text-sm text-gray-600 text-center">
                Nessuna relazione trovata
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
