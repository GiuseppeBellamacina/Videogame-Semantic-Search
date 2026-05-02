import { useEffect, useMemo, useRef, useState } from "react";
import {
  X,
  Loader2,
  Trash2,
  ArrowRight,
  ArrowLeft,
  GitFork,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
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
  graphNodeIds: Set<string>;
  onNavigate: (uri: string) => void;
  onGraphExpand: (graph: GraphData) => void;
  onRemoveNode: (uri: string) => void;
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

interface RelGroup {
  predicate: string;
  type: string;
  items: { uri: string; label: string; type: string }[];
  direction: "out" | "in";
}

export function NodeContextMenu({
  node,
  x,
  y,
  graphNodeIds,
  onNavigate,
  onGraphExpand,
  onRemoveNode,
  onClose,
}: NodeContextMenuProps) {
  const [details, setDetails] = useState<NodeDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
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

  // Group relations by predicate
  const groups = useMemo<RelGroup[]>(() => {
    if (!details) return [];
    const gMap = new Map<string, RelGroup>();

    for (const r of details.outgoing_relations) {
      const key = `out:${r.predicate}`;
      if (!gMap.has(key)) {
        gMap.set(key, {
          predicate: r.predicate,
          type: r.target_type,
          items: [],
          direction: "out",
        });
      }
      gMap.get(key)!.items.push({
        uri: r.target_uri,
        label: r.target_label,
        type: r.target_type,
      });
    }

    for (const r of details.incoming_relations) {
      const key = `in:${r.predicate}`;
      if (!gMap.has(key)) {
        gMap.set(key, {
          predicate: r.predicate,
          type: r.source_type,
          items: [],
          direction: "in",
        });
      }
      gMap.get(key)!.items.push({
        uri: r.source_uri,
        label: r.source_label,
        type: r.source_type,
      });
    }

    return [...gMap.values()];
  }, [details]);

  // Count total new nodes
  const newAllCount = useMemo(() => {
    const uris = new Set<string>();
    for (const g of groups) {
      for (const item of g.items) uris.add(item.uri);
    }
    uris.delete(node.id);
    return [...uris].filter((u) => !graphNodeIds.has(u)).length;
  }, [groups, node.id, graphNodeIds]);

  function toggleGroup(key: string) {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function expandGroup(group: RelGroup) {
    const nodes: GraphNode[] = [];
    const links: { source: string; target: string; label: string }[] = [];
    const seenUris = new Set<string>();

    for (const item of group.items) {
      if (!seenUris.has(item.uri)) {
        nodes.push(makeNode(item.uri, item.label, item.type));
        seenUris.add(item.uri);
      }
      if (group.direction === "out") {
        links.push({
          source: node.id,
          target: item.uri,
          label: group.predicate,
        });
      } else {
        links.push({
          source: item.uri,
          target: node.id,
          label: group.predicate,
        });
      }
    }
    onGraphExpand({ nodes, links });
    onClose();
  }

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
  }

  function expandAll() {
    const nodes: GraphNode[] = [];
    const links: { source: string; target: string; label: string }[] = [];
    const seenUris = new Set<string>();
    for (const g of groups) {
      for (const item of g.items) {
        if (!seenUris.has(item.uri)) {
          nodes.push(makeNode(item.uri, item.label, item.type));
          seenUris.add(item.uri);
        }
        if (g.direction === "out") {
          links.push({ source: node.id, target: item.uri, label: g.predicate });
        } else {
          links.push({ source: item.uri, target: node.id, label: g.predicate });
        }
      }
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

      {/* Open in sidebar + Remove */}
      <div className="px-4 py-2 border-b border-gray-800 flex items-center justify-between">
        <button
          onClick={() => {
            onNavigate(node.id);
            onClose();
          }}
          className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
        >
          Apri nella sidebar →
        </button>
        <button
          onClick={() => onRemoveNode(node.id)}
          title="Rimuovi dal grafo"
          className="flex items-center gap-1 text-xs text-red-500 hover:text-red-400 transition-colors"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Rimuovi
        </button>
      </div>

      {/* Content — grouped by predicate */}
      <div className="max-h-64 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center py-8 text-gray-500">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            <span className="text-sm">Caricamento relazioni...</span>
          </div>
        )}

        {error && <div className="px-4 py-3 text-sm text-red-400">{error}</div>}

        {details && groups.length > 0 && (
          <div className="divide-y divide-gray-800/60">
            {groups.map((group) => {
              const key = `${group.direction}:${group.predicate}`;
              const isExpanded = expandedGroups.has(key);
              const newInGroup = group.items.filter(
                (item) => !graphNodeIds.has(item.uri),
              ).length;

              return (
                <div key={key}>
                  {/* Group header — clickable to expand items list */}
                  <div className="flex items-center">
                    <button
                      onClick={() => toggleGroup(key)}
                      className="flex-1 flex items-center gap-2 px-4 py-2.5 hover:bg-gray-800/50 transition-colors text-left"
                    >
                      {group.direction === "out" ? (
                        <ArrowRight className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                      ) : (
                        <ArrowLeft className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                      )}
                      <span className="text-xs text-gray-300 flex-1">
                        {group.predicate}
                      </span>
                      <span className="text-[10px] text-gray-500 mr-1">
                        {group.items.length}
                      </span>
                      {isExpanded ? (
                        <ChevronDown className="w-3 h-3 text-gray-500" />
                      ) : (
                        <ChevronRight className="w-3 h-3 text-gray-500" />
                      )}
                    </button>
                    {/* Expand all in this group */}
                    {newInGroup > 0 && (
                      <button
                        onClick={() => expandGroup(group)}
                        title={`Espandi tutti (${group.items.length})`}
                        className="px-2 py-2.5 text-[10px] font-mono text-indigo-500 hover:text-indigo-300 hover:bg-gray-800/50 transition-colors"
                      >
                        +{newInGroup}
                      </button>
                    )}
                  </div>

                  {/* Expanded items */}
                  {isExpanded && (
                    <div className="bg-gray-800/20">
                      {group.items.map((item, i) => (
                        <button
                          key={i}
                          onClick={() =>
                            expandSingle(
                              item.uri,
                              item.label,
                              item.type,
                              group.predicate,
                              group.direction,
                            )
                          }
                          className="w-full px-6 py-1.5 flex items-center gap-2 hover:bg-gray-800 transition-colors text-left"
                        >
                          <span className="text-xs text-gray-300 truncate flex-1">
                            {item.label}
                          </span>
                          {!graphNodeIds.has(item.uri) && (
                            <span className="text-[10px] text-indigo-500 font-mono flex-shrink-0">
                              +1
                            </span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {details && groups.length === 0 && !loading && (
          <p className="px-4 py-6 text-sm text-gray-600 text-center">
            Nessuna relazione trovata
          </p>
        )}
      </div>

      {/* Footer — expand all */}
      {details && newAllCount > 0 && (
        <div className="border-t border-gray-800 p-3">
          <button
            onClick={expandAll}
            className="w-full flex items-center gap-2 px-3 py-2 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 text-xs rounded-lg transition-colors"
          >
            <GitFork className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Espandi tutti nel grafo</span>
            <span className="ml-auto font-semibold">+{newAllCount} nuovi</span>
          </button>
        </div>
      )}
    </div>
  );
}
