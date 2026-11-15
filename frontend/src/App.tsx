import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { Code2, List, Network, Sparkles, SlidersHorizontal } from "lucide-react";
import { SearchBar } from "@/components/SearchBar";
import { QueryBuilder } from "@/components/QueryBuilder";
import { DEFAULT_QUERY, SparqlEditor } from "@/components/SparqlEditor";
import { ResultList } from "@/components/ResultList";
import { KnowledgeGraph } from "@/components/KnowledgeGraph";
import { NodeDetail } from "@/components/NodeDetail";
import { NodeContextMenu } from "@/components/NodeContextMenu";
import { SparqlViewer } from "@/components/SparqlViewer";
import { useQuery } from "@/hooks/useQuery";
import { getCrossLinks } from "@/lib/api";
import { SUGGESTIONS } from "@/lib/queryCache";
import type {
  BuilderRequest,
  GraphData,
  GraphLink,
  GraphNode,
} from "@/types";

type Mode = "nl" | "builder" | "sparql";

const EDITOR_KEY = "vg:editor-query";
const loadEditorText = () => {
  try {
    return localStorage.getItem(EDITOR_KEY) || DEFAULT_QUERY;
  } catch {
    return DEFAULT_QUERY;
  }
};

const endId = (e: string | GraphNode) => (typeof e === "string" ? e : e.id);
const linkKey = (l: GraphLink) => `${endId(l.source)}__${endId(l.target)}__${l.label}`;
const reverseKey = (l: GraphLink) => `${endId(l.target)}__${endId(l.source)}__${l.label}`;

export default function App() {
  const { data, loading, error, progress, search, searchBuilder, searchSparql, cancel, reset } =
    useQuery();
  const [mode, setMode] = useState<Mode>("nl");
  const [seed, setSeed] = useState("");
  const [editorText, setEditorText] = useState(loadEditorText);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [highlightNode, setHighlightNode] = useState<string | null>(null);
  const [mobileTab, setMobileTab] = useState<"results" | "graph">("results");
  const [contextMenu, setContextMenu] = useState<{
    node: GraphNode;
    x: number;
    y: number;
  } | null>(null);
  const [extraGraph, setExtraGraph] = useState<GraphData>({ nodes: [], links: [] });
  const [hiddenNodeIds, setHiddenNodeIds] = useState<Set<string>>(new Set());
  const [deletedNodeIds, setDeletedNodeIds] = useState<Set<string>>(new Set());

  const resetCanvas = useCallback(() => {
    setExtraGraph({ nodes: [], links: [] });
    setHiddenNodeIds(new Set());
    setDeletedNodeIds(new Set());
    setSelectedNode(null);
    setHighlightNode(null);
  }, []);

  const handleSearch = useCallback(
    (query: string) => {
      resetCanvas();
      search(query);
    },
    [resetCanvas, search],
  );

  const handleBuilderRun = useCallback(
    (body: BuilderRequest) => {
      resetCanvas();
      searchBuilder(body);
    },
    [resetCanvas, searchBuilder],
  );

  const changeEditorText = useCallback((q: string) => {
    setEditorText(q);
    try {
      localStorage.setItem(EDITOR_KEY, q);
    } catch {
      /* storage unavailable */
    }
  }, []);

  const handleSparqlRun = useCallback(
    (q: string) => {
      resetCanvas();
      searchSparql(q);
    },
    [resetCanvas, searchSparql],
  );

  // "Modifica" on any query shown in the results: open it in the editor
  const handleEditQuery = useCallback(
    (q: string) => {
      changeEditorText(q);
      setMode("sparql");
    },
    [changeEditorText],
  );

  const handleRemoveNode = useCallback(
    (uri: string) => {
      setHiddenNodeIds((prev) => new Set([...prev, uri]));
      setContextMenu(null);
      if (selectedNode === uri) {
        setSelectedNode(null);
        setHighlightNode(null);
      }
    },
    [selectedNode],
  );

  const sceneIds = useRef<string[]>([]);

  const handleGraphExpand = useCallback(async (newGraph: GraphData) => {
    // Un-hide any node being re-added (e.g. previously removed, now re-expanded)
    const incomingIds = new Set(newGraph.nodes.map((n) => n.id));
    const without = (prev: Set<string>) => {
      const next = new Set([...prev].filter((id) => !incomingIds.has(id)));
      return next.size === prev.size ? prev : next;
    };
    setHiddenNodeIds(without);
    setDeletedNodeIds(without);

    // everything on the scene (the search result too, not only what was added by hand)
    const existingNodeIds = sceneIds.current;
    const onScene = new Set(existingNodeIds);
    const addedNodeIds = newGraph.nodes.map((n) => n.id).filter((id) => !onScene.has(id));

    setExtraGraph((prev) => {
      const existingIds = new Set(prev.nodes.map((n) => n.id));
      const existingLinkKeys = new Set(prev.links.map(linkKey));
      const addedNodes = newGraph.nodes.filter((n) => !existingIds.has(n.id));
      const addedLinks = newGraph.links.filter((l) => !existingLinkKeys.has(linkKey(l)));
      return {
        nodes: [...prev.nodes, ...addedNodes],
        links: [...prev.links, ...addedLinks],
      };
    });

    // Discover links between the new nodes and what is already on the canvas
    if (addedNodeIds.length === 0) return;
    try {
      const crossLinks = await getCrossLinks(existingNodeIds, addedNodeIds);
      if (crossLinks.length === 0) return;
      setExtraGraph((prev) => {
        const keys = new Set(prev.links.map(linkKey));
        const fresh = crossLinks.filter(
          (l) => !keys.has(linkKey(l)) && !keys.has(reverseKey(l)),
        );
        return fresh.length ? { ...prev, links: [...prev.links, ...fresh] } : prev;
      });
    } catch {
      // best-effort
    }
  }, []);

  const handleNodeClick = useCallback((uri: string) => {
    setHighlightNode(uri);
    if (window.innerWidth >= 640) setSelectedNode(uri);
    setMobileTab("graph");
  }, []);

  const handleOpenSidebar = useCallback((uri: string) => {
    setSelectedNode(uri);
    setHighlightNode(uri);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedNode(null);
    setHighlightNode(null);
  }, []);

  // a click on nothing (outside the side panel, the graph tools and any control) lets go of
  // the open panel, the context menu and the focused node; the canvas reports its own empty clicks
  const clearFocus = useCallback(() => {
    setSelectedNode(null);
    setHighlightNode(null);
    setContextMenu(null);
  }, []);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      const t = e.target as HTMLElement | null;
      if (!t?.closest || !t.isConnected) return;
      if (t.closest("[data-detail], [data-context-menu], [data-graph], button, a, input, textarea, select, label, [role=option], [role=listbox]")) return;
      clearFocus();
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, [clearFocus]);

  const handleNodeRightClick = useCallback((node: GraphNode, x: number, y: number) => {
    setContextMenu({ node, x, y });
  }, []);

  // every node known to the page, hidden or not: the result list still needs their type and picture
  const allNodes = useMemo(() => {
    const base = data?.graph?.nodes ?? [];
    const ids = new Set(base.map((n) => n.id));
    return [...base, ...extraGraph.nodes.filter((n) => !ids.has(n.id))];
  }, [data, extraGraph]);

  const mergedGraph = useMemo<GraphData>(() => {
    const base = data?.graph ?? { nodes: [], links: [] };
    const baseIds = new Set(base.nodes.map((n) => n.id));
    const baseKeys = new Set(base.links.map(linkKey));
    const nodes = [
      ...base.nodes,
      ...extraGraph.nodes.filter((n) => !baseIds.has(n.id)),
    ].filter((n) => !hiddenNodeIds.has(n.id) && !deletedNodeIds.has(n.id));
    const visible = new Set(nodes.map((n) => n.id));
    const links = [
      ...base.links,
      ...extraGraph.links.filter((l) => !baseKeys.has(linkKey(l))),
    ].filter((l) => visible.has(endId(l.source)) && visible.has(endId(l.target)));
    return { nodes, links };
  }, [data, extraGraph, hiddenNodeIds, deletedNodeIds]);

  useEffect(() => {
    sceneIds.current = mergedGraph.nodes.map((n) => n.id);
  }, [mergedGraph]);

  // Isolate: keep only the given nodes (the rest is hidden; "Mostra tutto" brings it back)
  const handleClear = useCallback(() => {
    cancel();
    reset();
    resetCanvas();
  }, [cancel, reset, resetCanvas]);

  const handleKeepOnly = useCallback(
    (ids: string[]) => {
      const keep = new Set(ids);
      setHiddenNodeIds(
        (prev) => new Set([...prev, ...mergedGraph.nodes.filter((n) => !keep.has(n.id)).map((n) => n.id)]),
      );
      setContextMenu(null);
    },
    [mergedGraph.nodes],
  );

  // Delete: gone from the scene for good (re-expanding a node can bring one back)
  const handleDeleteMany = useCallback((ids: string[]) => {
    setDeletedNodeIds((prev) => new Set([...prev, ...ids]));
    setHiddenNodeIds((prev) => new Set([...prev].filter((id) => !ids.includes(id))));
    setSelectedNode((sel) => (sel && ids.includes(sel) ? null : sel));
    setHighlightNode((h) => (h && ids.includes(h) ? null : h));
    setContextMenu(null);
  }, []);

  const handleDeleteHidden = useCallback(
    (typeHiddenIds: string[]) => {
      setDeletedNodeIds((prev) => new Set([...prev, ...hiddenNodeIds, ...typeHiddenIds]));
      setHiddenNodeIds(new Set());
    },
    [hiddenNodeIds],
  );

  const handleHideMany = useCallback((ids: string[]) => {
    setHiddenNodeIds((prev) => new Set([...prev, ...ids]));
    setSelectedNode(null);
    setHighlightNode(null);
  }, []);

  const graphNodeIds = useMemo(
    () => new Set(mergedGraph.nodes.map((n) => n.id)),
    [mergedGraph],
  );

  const modes = [
    ["nl", "Fai una domanda", Sparkles],
    ["builder", "Usa i filtri", SlidersHorizontal],
    ["sparql", "Editor SPARQL", Code2],
  ] as const;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="relative z-40 flex-shrink-0 border-b border-rule">
        <div className="mx-auto max-w-[1920px] px-4 py-4 sm:px-8">
          <div className="mb-3 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
            <div>
              <h1 className="font-serif text-[26px] leading-none tracking-tight">
                Videogame Semantic Search
              </h1>
              <p className="label mt-1.5 hidden sm:block">
                Grafo di conoscenza · OWL 2 · SPARQL
              </p>
            </div>
            <div
              role="tablist"
              aria-label="Modalità di ricerca"
              className="inline-flex rounded-sm border border-rule bg-panel p-0.5"
            >
              {modes.map(([m, label, Icon]) => (
                <button
                  key={m}
                  role="tab"
                  aria-selected={mode === m}
                  onClick={() => setMode(m)}
                  className={`inline-flex items-center gap-2 rounded-[3px] px-3.5 py-1.5 text-sm transition-colors ${
                    mode === m ? "bg-raised text-ink" : "text-mute hover:text-ink"
                  }`}
                >
                  <Icon className={`h-3.5 w-3.5 ${mode === m ? "text-brick" : ""}`} />
                  {label}
                </button>
              ))}
            </div>
          </div>
          {/* both stay mounted: switching mode keeps the filters you built */}
          <div className="max-w-5xl">
            <div className={mode === "nl" ? "" : "hidden"}>
              <SearchBar
                onSearch={handleSearch}
                onCancel={cancel}
                loading={loading}
                progress={progress}
                seed={seed}
              />
            </div>
            <div className={mode === "builder" ? "" : "hidden"}>
              <QueryBuilder onRun={handleBuilderRun} onCancel={cancel} loading={loading} />
            </div>
            <div className={mode === "sparql" ? "" : "hidden"}>
              <SparqlEditor
                value={editorText}
                onChange={changeEditorText}
                onRun={handleSparqlRun}
                onCancel={cancel}
                loading={loading}
              />
            </div>
          </div>
        </div>
      </header>

      <div className="flex flex-shrink-0 border-b border-rule md:hidden">
        {(
          [
            ["results", "Risultati", List],
            ["graph", "Grafo", Network],
          ] as const
        ).map(([id, label, Icon]) => (
          <button
            key={id}
            onClick={() => setMobileTab(id)}
            className={`flex flex-1 items-center justify-center gap-2 py-2.5 text-sm ${
              mobileTab === id ? "border-b border-brick text-ink" : "text-mute"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      <main className="flex min-h-0 flex-1 overflow-hidden">
        <section
          className={`${mobileTab === "results" ? "flex" : "hidden"} w-full flex-shrink-0 flex-col overflow-hidden border-rule md:flex md:w-[400px] md:border-r`}
        >
          <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
            {error && (
              <div className="border-l-2 border-brick pl-3 text-sm animate-fade-in">
                <p className="label text-brick">Errore</p>
                <p className="mt-1 text-ink">{error}</p>
              </div>
            )}

            {loading && progress?.sparql && <SparqlViewer sparql={progress.sparql} live />}

            {loading && (
              <ul className="rule-y" aria-hidden>
                {[0, 1, 2, 3].map((i) => (
                  <li key={i} className="flex gap-3 py-3">
                    <div className="h-[52px] w-[39px] animate-shimmer rounded-[3px] bg-raised" />
                    <div className="flex-1 space-y-2 pt-1">
                      <div className="h-3.5 w-2/3 animate-shimmer rounded-sm bg-raised" />
                      <div className="h-2.5 w-1/3 animate-shimmer rounded-sm bg-raised" />
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {!loading && data && (
              <>
                <SparqlViewer sparql={data.sparql} success={data.success} onEdit={handleEditQuery} />
                {data.truncated && (
                  <p className="text-[13px] text-mute">
                    Mostrate le prime {data.total_rows} righe: aggiungi un filtro o un LIMIT per restringere.
                  </p>
                )}
                <ResultList
                  results={data.results}
                  totalRows={data.total_rows}
                  nodes={allNodes}
                  onNodeClick={handleNodeClick}
                />
              </>
            )}

            {!loading && !data && !error && (
              <div className="pt-6 animate-fade-in">
                <h2 className="font-serif text-3xl leading-tight">
                  Esplora il grafo dei videogiochi
                </h2>
                <p className="mt-3 text-[15px] leading-relaxed text-mute">
                  Fai una domanda in italiano oppure usa i filtri. Ogni risultato
                  diventa un grafo che puoi espandere nodo per nodo.
                </p>
                <ul className="rule-y mt-6">
                  {SUGGESTIONS.slice(0, 5).map((q) => (
                    <li key={q}>
                      <button
                        onClick={() => {
                          setMode("nl");
                          setSeed(q);
                          handleSearch(q);
                        }}
                        className="w-full py-2.5 text-left text-sm hover:text-brick"
                      >
                        {q}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>

        <section
          data-graph
          className={`${mobileTab === "graph" ? "flex" : "hidden"} relative h-full min-h-0 w-full flex-1 md:flex`}
        >
          <KnowledgeGraph
            data={mergedGraph}
            loading={loading}
            onNodeClick={handleNodeClick}
            highlightNode={highlightNode}
            onNodeRightClick={handleNodeRightClick}
            onBackgroundClick={clearFocus}
            onExpand={handleGraphExpand}
            hiddenCount={hiddenNodeIds.size}
            onRestoreHidden={() => setHiddenNodeIds(new Set())}
            onKeepOnly={handleKeepOnly}
            onClear={handleClear}
            onDeleteMany={handleDeleteMany}
            onDeleteHidden={handleDeleteHidden}
            onHideMany={handleHideMany}
          />
        </section>
      </main>

      <NodeDetail
        uri={selectedNode}
        onClose={handleCloseDetail}
        onNavigate={handleNodeClick}
        onGraphExpand={handleGraphExpand}
      />

      {contextMenu && (
        <NodeContextMenu
          node={contextMenu.node}
          x={contextMenu.x}
          y={contextMenu.y}
          graphNodeIds={graphNodeIds}
          onNavigate={handleOpenSidebar}
          onGraphExpand={handleGraphExpand}
          onRemoveNode={handleRemoveNode}
          onDeleteNode={(uri) => handleDeleteMany([uri])}
          onClose={() => setContextMenu(null)}
        />
      )}
    </div>
  );
}
