import { useState, useCallback } from "react";
import { Gamepad2, BarChart3 } from "lucide-react";
import { SearchBar } from "@/components/SearchBar";
import { ResultList } from "@/components/ResultList";
import { KnowledgeGraph } from "@/components/KnowledgeGraph";
import { NodeDetail } from "@/components/NodeDetail";
import { SparqlViewer } from "@/components/SparqlViewer";
import { AddGameForm } from "@/components/AddGameForm";
import { useQuery } from "@/hooks/useQuery";
import type { GraphData } from "@/types";

export default function App() {
  const { data, loading, error, search } = useQuery();
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [highlightNode, setHighlightNode] = useState<string | null>(null);

  const handleNodeClick = useCallback((uri: string) => {
    setSelectedNode(uri);
    setHighlightNode(uri);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedNode(null);
    setHighlightNode(null);
  }, []);

  const graphData: GraphData = data?.graph || { nodes: [], links: [] };

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm">
        <div className="max-w-[1920px] mx-auto px-6 py-4">
          <div className="flex items-center gap-4 mb-4">
            <div className="p-2 bg-indigo-600/20 rounded-xl">
              <Gamepad2 className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">
                Videogame Semantic Search
              </h1>
              <p className="text-xs text-gray-500">
                Knowledge Graph Explorer · Powered by OWL + SPARQL + GPT-4.1
              </p>
            </div>
          </div>
          <SearchBar onSearch={search} loading={loading} />
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left panel: Results */}
        <div className="w-[420px] flex-shrink-0 border-r border-gray-800 flex flex-col overflow-hidden">
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

            {/* Add Game Form */}
            <AddGameForm />
          </div>
        </div>

        {/* Right panel: Knowledge Graph */}
        <div className="flex-1 relative bg-gray-950">
          <KnowledgeGraph
            data={graphData}
            onNodeClick={handleNodeClick}
            highlightNode={highlightNode}
          />
        </div>
      </main>

      {/* Node Detail Panel */}
      <NodeDetail
        uri={selectedNode}
        onClose={handleCloseDetail}
        onNavigate={handleNodeClick}
      />
    </div>
  );
}
