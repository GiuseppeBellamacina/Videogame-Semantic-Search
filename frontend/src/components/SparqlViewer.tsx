import { useState } from "react";
import { ChevronDown, ChevronUp, Code } from "lucide-react";

interface SparqlViewerProps {
  sparql: string;
  success: boolean;
}

export function SparqlViewer({ sparql, success }: SparqlViewerProps) {
  const [showSparql, setShowSparql] = useState(false);

  if (!sparql) return null;

  return (
    <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-4 animate-fade-in">
      <button
        onClick={() => setShowSparql(!showSparql)}
        className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-300 transition-colors"
      >
        <Code className="w-3.5 h-3.5" />
        <span>Query SPARQL generata</span>
        <span
          className={`ml-2 w-2 h-2 rounded-full ${
            success ? "bg-emerald-400" : "bg-amber-400"
          }`}
        />
        {showSparql ? (
          <ChevronUp className="w-3.5 h-3.5" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5" />
        )}
      </button>

      {showSparql && (
        <pre className="mt-2 p-3 bg-gray-950 border border-gray-800 rounded-lg text-xs text-gray-400 overflow-x-auto font-mono leading-relaxed">
          {sparql}
        </pre>
      )}
    </div>
  );
}
