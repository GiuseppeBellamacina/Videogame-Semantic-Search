import { useEffect, useState, useMemo } from "react";
import {
  X,
  Loader2,
  ExternalLink,
  ArrowRight,
  ArrowLeft,
  ChevronDown,
} from "lucide-react";
import type { NodeDetails, GraphData, GraphNode } from "@/types";
import { getNodeDetails } from "@/lib/api";

interface NodeDetailProps {
  uri: string | null;
  onClose: () => void;
  onNavigate: (uri: string) => void;
  onGraphExpand?: (graph: GraphData) => void;
}

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

const NODE_SIZES: Record<string, number> = {
  VideoGame: 9,
  Developer: 8,
  Publisher: 8,
  Genre: 6,
  Platform: 6,
  Character: 5,
  Franchise: 10,
  Award: 7,
  GameEngine: 7,
  Unknown: 5,
};

function makeNode(uri: string, label: string, type: string): GraphNode {
  return {
    id: uri,
    label,
    type,
    color: NODE_COLORS[type] ?? NODE_COLORS.Unknown,
    size: NODE_SIZES[type] ?? NODE_SIZES.Unknown,
    autoFetchImage: type === "VideoGame",
  };
}

const TYPE_BADGES: Record<string, string> = {
  VideoGame: "bg-indigo-500/20 text-indigo-300",
  Developer: "bg-amber-500/20 text-amber-300",
  Publisher: "bg-emerald-500/20 text-emerald-300",
  Genre: "bg-red-500/20 text-red-300",
  Platform: "bg-blue-500/20 text-blue-300",
  Character: "bg-pink-500/20 text-pink-300",
  Franchise: "bg-violet-500/20 text-violet-300",
  Award: "bg-orange-500/20 text-orange-300",
};

export function NodeDetail({
  uri,
  onClose,
  onNavigate,
  onGraphExpand,
}: NodeDetailProps) {
  const [details, setDetails] = useState<NodeDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!uri) {
      setDetails(null);
      return;
    }

    setLoading(true);
    setError(null);
    setExpandedGroups(new Set());

    getNodeDetails(uri)
      .then((res) => {
        setDetails(res.details);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [uri]);

  // Group outgoing relations by predicate
  const outGroups = useMemo(() => {
    if (!details) return [];
    const map = new Map<string, typeof details.outgoing_relations>();
    for (const rel of details.outgoing_relations) {
      if (!map.has(rel.predicate)) map.set(rel.predicate, []);
      map.get(rel.predicate)!.push(rel);
    }
    return [...map.entries()].map(([pred, items]) => ({
      predicate: pred,
      items,
    }));
  }, [details]);

  // Group incoming relations by predicate
  const inGroups = useMemo(() => {
    if (!details) return [];
    const map = new Map<string, typeof details.incoming_relations>();
    for (const rel of details.incoming_relations) {
      if (!map.has(rel.predicate)) map.set(rel.predicate, []);
      map.get(rel.predicate)!.push(rel);
    }
    return [...map.entries()].map(([pred, items]) => ({
      predicate: pred,
      items,
    }));
  }, [details]);

  function toggleGroup(key: string) {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  if (!uri) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-96 bg-gray-900 border-l border-gray-700 shadow-2xl z-50 animate-slide-in overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-gray-900/95 backdrop-blur-sm border-b border-gray-800 p-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white truncate">
          {details?.label || "Dettagli"}
        </h2>
        <button
          onClick={onClose}
          className="p-1.5 hover:bg-gray-800 rounded-lg transition-colors"
        >
          <X className="w-5 h-5 text-gray-400" />
        </button>
      </div>

      <div className="p-4 space-y-6">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
          </div>
        )}

        {error && (
          <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg p-3">
            {error}
          </div>
        )}

        {details && !loading && (
          <>
            {/* Type badge — only if meaningful */}
            {details.type &&
              details.type !== "Unknown" &&
              details.type !== "Thing" && (
                <div className="flex items-center gap-2">
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${
                      TYPE_BADGES[details.type] || "bg-gray-700 text-gray-300"
                    }`}
                  >
                    {details.type}
                  </span>
                </div>
              )}

            {/* Properties */}
            {Object.keys(details.properties).length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
                  Proprietà
                </h3>
                <div className="space-y-2">
                  {Object.entries(details.properties).map(([key, value]) => (
                    <div key={key} className="bg-gray-800/50 rounded-lg p-3">
                      <div className="text-xs text-gray-500 mb-1">{key}</div>
                      <div className="text-sm text-gray-200 break-words">
                        {value.length > 300
                          ? value.slice(0, 300) + "..."
                          : value}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Outgoing relations — grouped by predicate */}
            {outGroups.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide flex items-center gap-1">
                  <ArrowRight className="w-3.5 h-3.5" />
                  Relazioni in uscita ({details.outgoing_relations.length})
                </h3>
                <div className="space-y-1">
                  {outGroups.map((group) => {
                    const key = `out:${group.predicate}`;
                    const isExpanded = expandedGroups.has(key);
                    const PREVIEW = 3;
                    const showItems = isExpanded
                      ? group.items
                      : group.items.slice(0, PREVIEW);

                    return (
                      <div
                        key={key}
                        className="bg-gray-800/30 rounded-lg overflow-hidden"
                      >
                        <button
                          onClick={() => toggleGroup(key)}
                          className="w-full flex items-center gap-2 px-3 py-2 hover:bg-gray-800/60 transition-colors text-left"
                        >
                          <span className="text-xs font-medium text-gray-400 flex-1">
                            {group.predicate}
                          </span>
                          <span className="text-[10px] text-gray-500">
                            {group.items.length}
                          </span>
                          <ChevronDown
                            className={`w-3 h-3 text-gray-500 transition-transform ${isExpanded ? "" : "-rotate-90"}`}
                          />
                        </button>
                        <div className="px-1 pb-1 space-y-0.5">
                          {showItems.map((rel, i) => (
                            <button
                              key={i}
                              onClick={() => {
                                onNavigate(rel.target_uri);
                                if (onGraphExpand && uri) {
                                  const currentNode = makeNode(
                                    uri,
                                    details.label,
                                    details.type,
                                  );
                                  const targetNode = makeNode(
                                    rel.target_uri,
                                    rel.target_label,
                                    rel.target_type,
                                  );
                                  onGraphExpand({
                                    nodes: [currentNode, targetNode],
                                    links: [
                                      {
                                        source: uri,
                                        target: rel.target_uri,
                                        label: rel.predicate,
                                      },
                                    ],
                                  });
                                }
                              }}
                              className="w-full flex items-center gap-2 hover:bg-gray-800 rounded-md px-2 py-1.5 transition-colors text-left group"
                            >
                              <span className="text-sm text-indigo-400 group-hover:text-indigo-300 truncate flex-1">
                                {rel.target_label}
                              </span>
                              {rel.target_type &&
                                rel.target_type !== "Unknown" &&
                                rel.target_type !== "Thing" && (
                                  <span
                                    className={`text-[10px] px-1.5 py-0.5 rounded ${TYPE_BADGES[rel.target_type] || "bg-gray-700 text-gray-400"}`}
                                  >
                                    {rel.target_type}
                                  </span>
                                )}
                              <ExternalLink className="w-3 h-3 text-gray-600 group-hover:text-gray-400 flex-shrink-0" />
                            </button>
                          ))}
                          {!isExpanded && group.items.length > PREVIEW && (
                            <button
                              onClick={() => toggleGroup(key)}
                              className="w-full text-center text-[10px] text-gray-500 hover:text-gray-300 py-1"
                            >
                              +{group.items.length - PREVIEW} altri...
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Incoming relations — grouped by predicate */}
            {inGroups.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide flex items-center gap-1">
                  <ArrowLeft className="w-3.5 h-3.5" />
                  Relazioni in entrata ({details.incoming_relations.length})
                </h3>
                <div className="space-y-1">
                  {inGroups.map((group) => {
                    const key = `in:${group.predicate}`;
                    const isExpanded = expandedGroups.has(key);
                    const PREVIEW = 3;
                    const showItems = isExpanded
                      ? group.items
                      : group.items.slice(0, PREVIEW);

                    return (
                      <div
                        key={key}
                        className="bg-gray-800/30 rounded-lg overflow-hidden"
                      >
                        <button
                          onClick={() => toggleGroup(key)}
                          className="w-full flex items-center gap-2 px-3 py-2 hover:bg-gray-800/60 transition-colors text-left"
                        >
                          <span className="text-xs font-medium text-gray-400 flex-1">
                            {group.predicate}
                          </span>
                          <span className="text-[10px] text-gray-500">
                            {group.items.length}
                          </span>
                          <ChevronDown
                            className={`w-3 h-3 text-gray-500 transition-transform ${isExpanded ? "" : "-rotate-90"}`}
                          />
                        </button>
                        <div className="px-1 pb-1 space-y-0.5">
                          {showItems.map((rel, i) => (
                            <button
                              key={i}
                              onClick={() => {
                                onNavigate(rel.source_uri);
                                if (onGraphExpand && uri) {
                                  const currentNode = makeNode(
                                    uri,
                                    details.label,
                                    details.type,
                                  );
                                  const sourceNode = makeNode(
                                    rel.source_uri,
                                    rel.source_label,
                                    rel.source_type,
                                  );
                                  onGraphExpand({
                                    nodes: [currentNode, sourceNode],
                                    links: [
                                      {
                                        source: rel.source_uri,
                                        target: uri,
                                        label: rel.predicate,
                                      },
                                    ],
                                  });
                                }
                              }}
                              className="w-full flex items-center gap-2 hover:bg-gray-800 rounded-md px-2 py-1.5 transition-colors text-left group"
                            >
                              {rel.source_type &&
                                rel.source_type !== "Unknown" &&
                                rel.source_type !== "Thing" && (
                                  <span
                                    className={`text-[10px] px-1.5 py-0.5 rounded ${TYPE_BADGES[rel.source_type] || "bg-gray-700 text-gray-400"}`}
                                  >
                                    {rel.source_type}
                                  </span>
                                )}
                              <span className="text-sm text-indigo-400 group-hover:text-indigo-300 truncate flex-1">
                                {rel.source_label}
                              </span>
                              <ExternalLink className="w-3 h-3 text-gray-600 group-hover:text-gray-400 flex-shrink-0" />
                            </button>
                          ))}
                          {!isExpanded && group.items.length > PREVIEW && (
                            <button
                              onClick={() => toggleGroup(key)}
                              className="w-full text-center text-[10px] text-gray-500 hover:text-gray-300 py-1"
                            >
                              +{group.items.length - PREVIEW} altri...
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
