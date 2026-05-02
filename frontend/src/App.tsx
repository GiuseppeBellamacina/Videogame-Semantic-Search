import { useState, useCallback, useMemo } from "react";
import { Gamepad2, BarChart3, Github, List, Network } from "lucide-react";
import { SearchBar } from "@/components/SearchBar";
import { ResultList } from "@/components/ResultList";
import { KnowledgeGraph } from "@/components/KnowledgeGraph";
import { NodeDetail } from "@/components/NodeDetail";
import { NodeContextMenu } from "@/components/NodeContextMenu";
import { SparqlViewer } from "@/components/SparqlViewer";
import { Analytics } from "@vercel/analytics/react";
import { useQuery } from "@/hooks/useQuery";
import type { GraphData, GraphNode } from "@/types";

export default function App() {
  const { data, loading, error, search, cancel } = useQuery();
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [highlightNode, setHighlightNode] = useState<string | null>(null);
  const [mobileTab, setMobileTab] = useState<"results" | "graph">("results");
  const [contextMenu, setContextMenu] = useState<{
    node: GraphNode;
    x: number;
    y: number;
  } | null>(null);
  const [maxResults, setMaxResults] = useState(10);
  const [extraGraph, setExtraGraph] = useState<GraphData>({
    nodes: [],
    links: [],
  });

  const handleGraphExpand = useCallback((newGraph: GraphData) => {
    const taggedNodes = newGraph.nodes.map((n) =>
      n.type === "VideoGame" ? { ...n, autoFetchImage: true } : n,
    );

    setExtraGraph((prev) => {
      const existingNodeIds = new Set(prev.nodes.map((n) => n.id));
      const existingLinkKeys = new Set(
        prev.links.map(
          (l) =>
            `${typeof l.source === "string" ? l.source : l.source.id}__${typeof l.target === "string" ? l.target : l.target.id}__${l.label}`,
        ),
      );
      const addedNodes = taggedNodes.filter((n) => !existingNodeIds.has(n.id));
      const addedLinks = newGraph.links.filter((l) => {
        const key = `${typeof l.source === "string" ? l.source : l.source.id}__${typeof l.target === "string" ? l.target : l.target.id}__${l.label}`;
        return !existingLinkKeys.has(key);
      });
      return {
        nodes: [...prev.nodes, ...addedNodes],
        links: [...prev.links, ...addedLinks],
      };
    });
  }, []);

  const handleNodeClick = useCallback((uri: string) => {
    setSelectedNode(uri);
    setHighlightNode(uri);
    setMobileTab("graph");
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedNode(null);
    setHighlightNode(null);
  }, []);

  const handleNodeRightClick = useCallback(
    (node: GraphNode, x: number, y: number) => {
      setContextMenu({ node, x, y });
    },
    [],
  );

  const graphData: GraphData = useMemo(() => {
    const raw = data?.graph || { nodes: [], links: [] };
    return {
      ...raw,
      nodes: raw.nodes.map((n) =>
        n.type === "VideoGame" ? { ...n, autoFetchImage: true } : n,
      ),
    };
  }, [data]);

  const mergedGraph = useMemo<GraphData>(() => {
    const existingNodeIds = new Set(graphData.nodes.map((n) => n.id));
    const existingLinkKeys = new Set(
      graphData.links.map(
        (l) =>
          `${typeof l.source === "string" ? l.source : l.source.id}__${typeof l.target === "string" ? l.target : l.target.id}__${l.label}`,
      ),
    );
    const addedNodes = extraGraph.nodes.filter(
      (n) => !existingNodeIds.has(n.id),
    );
    const addedLinks = extraGraph.links.filter((l) => {
      const key = `${typeof l.source === "string" ? l.source : l.source.id}__${typeof l.target === "string" ? l.target : l.target.id}__${l.label}`;
      return !existingLinkKeys.has(key);
    });
    return {
      nodes: [...graphData.nodes, ...addedNodes],
      links: [...graphData.links, ...addedLinks],
    };
  }, [graphData, extraGraph]);

  const graphNodeIds = useMemo(
    () => new Set(mergedGraph.nodes.map((n) => n.id)),
    [mergedGraph],
  );

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm relative z-50">
        <div className="max-w-[1920px] mx-auto px-4 sm:px-6 py-3 sm:py-4">
          <div className="flex items-center justify-between gap-4 mb-3 sm:mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-600/20 rounded-xl">
                <Gamepad2 className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-400" />
              </div>
              <div>
                <h1 className="text-base sm:text-xl font-bold text-white leading-tight">
                  Videogame Semantic Search
                </h1>
                <p className="text-xs text-gray-500 hidden sm:block">
                  Knowledge Graph Explorer · Powered by OWL + SPARQL + GPT-4.1
                </p>
              </div>
            </div>
            <a
              href="https://github.com/GiuseppeBellamacina"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors text-sm"
            >
              <Github className="w-5 h-5" />
              <span className="hidden sm:inline">GiuseppeBellamacina</span>
            </a>
            <div className="hidden sm:flex items-center gap-2 text-xs text-gray-500">
              <label htmlFor="max-results" className="whitespace-nowrap">
                Max relazioni
              </label>
              <input
                id="max-results"
                type="number"
                min={1}
                max={200}
                value={maxResults}
                onChange={(e) =>
                  setMaxResults(
                    Math.max(1, Math.min(200, Number(e.target.value))),
                  )
                }
                className="w-16 px-2 py-1 bg-gray-800 border border-gray-700 rounded-lg text-white text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>
          <SearchBar onSearch={search} onCancel={cancel} loading={loading} />
        </div>
      </header>

      {/* Mobile tab bar */}
      <div className="md:hidden flex-shrink-0 flex border-b border-gray-800 bg-gray-950">
        <button
          onClick={() => setMobileTab("results")}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium transition-colors ${
            mobileTab === "results"
              ? "text-indigo-400 border-b-2 border-indigo-400"
              : "text-gray-500 hover:text-gray-300"
          }`}
        >
          <List className="w-4 h-4" />
          Risultati
        </button>
        <button
          onClick={() => setMobileTab("graph")}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium transition-colors ${
            mobileTab === "graph"
              ? "text-indigo-400 border-b-2 border-indigo-400"
              : "text-gray-500 hover:text-gray-300"
          }`}
        >
          <Network className="w-4 h-4" />
          Grafo
        </button>
      </div>

      {/* Main content */}
      <main className="flex-1 flex overflow-hidden min-h-0">
        {/* Results panel */}
        <div
          className={`${
            mobileTab === "results" ? "flex" : "hidden"
          } md:flex w-full md:w-[420px] flex-shrink-0 md:border-r border-gray-800 flex-col overflow-hidden`}
        >
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Error */}
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-300 text-sm animate-fade-in">
                <p className="font-medium">Errore</p>
                <p className="mt-1 text-red-400">{error}</p>
              </div>
            )}

            {/* SPARQL Query */}
            {data && (
              <SparqlViewer sparql={data.sparql} success={data.success} />
            )}

            {/* Results */}
            {data && (
              <ResultList
                results={data.results}
                totalRows={data.total_rows}
                onNodeClick={handleNodeClick}
              />
            )}

            {/* Empty state */}
            {!data && !error && !loading && (
              <div className="flex flex-col items-center justify-center h-full text-center py-20">
                <div className="p-4 bg-gray-800/50 rounded-2xl mb-4">
                  <BarChart3 className="w-10 h-10 text-gray-600" />
                </div>
                <h3 className="text-lg font-medium text-gray-400 mb-2">
                  Esplora il Knowledge Graph
                </h3>
                <p className="text-sm text-gray-600 max-w-[280px]">
                  Scrivi una domanda in linguaggio naturale per esplorare
                  l'ontologia dei videogiochi
                </p>
              </div>
            )}

            {/* Loading state */}
            {loading && (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className="bg-gray-900/80 border border-gray-800 rounded-xl p-4 animate-pulse"
                  >
                    <div className="h-4 bg-gray-800 rounded w-3/4 mb-2" />
                    <div className="h-3 bg-gray-800 rounded w-1/2" />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Graph panel */}
        <div
          className={`${
            mobileTab === "graph" ? "flex" : "hidden"
          } md:flex flex-1 relative bg-gray-950 w-full h-full min-h-0`}
        >
          <div className="flex-1 h-full w-full min-h-0">
            <KnowledgeGraph
              data={mergedGraph}
              onNodeClick={handleNodeClick}
              highlightNode={highlightNode}
              onNodeRightClick={handleNodeRightClick}
            />
          </div>
        </div>
      </main>

      {/* Node Detail Panel */}
      <NodeDetail
        uri={selectedNode}
        onClose={handleCloseDetail}
        onNavigate={handleNodeClick}
        onGraphExpand={handleGraphExpand}
      />

      {/* Node Context Menu (right-click) */}
      {contextMenu && (
        <NodeContextMenu
          node={contextMenu.node}
          x={contextMenu.x}
          y={contextMenu.y}
          maxResults={maxResults}
          graphNodeIds={graphNodeIds}
          onNavigate={handleNodeClick}
          onGraphExpand={handleGraphExpand}
          onClose={() => setContextMenu(null)}
        />
      )}

      <Analytics />
    </div>
  );
}
