import { useState, useCallback } from "react";
import { Gamepad2, BarChart3, Github, List, Network } from "lucide-react";
import { SearchBar } from "@/components/SearchBar";
import { ResultList } from "@/components/ResultList";
import { KnowledgeGraph } from "@/components/KnowledgeGraph";
import { NodeDetail } from "@/components/NodeDetail";
import { SparqlViewer } from "@/components/SparqlViewer";
import { Analytics } from "@vercel/analytics/react";
import { useQuery } from "@/hooks/useQuery";
import type { GraphData } from "@/types";

export default function App() {
  const { data, loading, error, search, cancel } = useQuery();
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [highlightNode, setHighlightNode] = useState<string | null>(null);
  const [mobileTab, setMobileTab] = useState<"results" | "graph">("results");

  const handleNodeClick = useCallback((uri: string) => {
    setSelectedNode(uri);
    setHighlightNode(uri);
    setMobileTab("graph");
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedNode(null);
    setHighlightNode(null);
  }, []);

  const graphData: GraphData = data?.graph || { nodes: [], links: [] };

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
      <main className="flex-1 flex overflow-hidden">
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
          } md:flex flex-1 relative bg-gray-950 w-full`}
        >
          <div className="flex-1 h-full w-full">
            <KnowledgeGraph
              data={graphData}
              onNodeClick={handleNodeClick}
              highlightNode={highlightNode}
            />
          </div>
        </div>
      </main>

      {/* Node Detail Panel */}
      <NodeDetail
        uri={selectedNode}
        onClose={handleCloseDetail}
        onNavigate={handleNodeClick}
      />

      <Analytics />
    </div>
  );
}
