import { useEffect, useRef, useState } from "react";
import { X, Loader2, ArrowRight, ArrowLeft } from "lucide-react";
import { getNodeDetails } from "@/lib/api";
import type { GraphNode, NodeDetails } from "@/types";

interface NodeContextMenuProps {
  node: GraphNode;
  x: number;
  y: number;
  maxResults: number;
  onNavigate: (uri: string) => void;
  onClose: () => void;
}

export function NodeContextMenu({
  node,
  x,
  y,
  maxResults,
  onNavigate,
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

  const outgoing = details?.outgoing_relations.slice(0, maxResults) ?? [];
  const incoming = details?.incoming_relations.slice(0, maxResults) ?? [];
  const outgoingTotal = details?.outgoing_relations.length ?? 0;
  const incomingTotal = details?.incoming_relations.length ?? 0;

  const shownOut = filter === "incoming" ? [] : outgoing;
  const shownIn = filter === "outgoing" ? [] : incoming;

  return (
    <div
      ref={menuRef}
      style={style}
      className="w-80 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl overflow-hidden animate-fade-in"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-gray-900/95">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-white truncate">
            {node.label}
          </p>
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
