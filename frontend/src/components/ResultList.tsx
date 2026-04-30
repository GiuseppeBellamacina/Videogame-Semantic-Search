import { ExternalLink } from "lucide-react";
import type { QueryResult } from "@/types";

interface ResultListProps {
  results: QueryResult[];
  totalRows: number;
  onNodeClick: (uri: string) => void;
}

const TYPE_COLORS: Record<string, string> = {
  VideoGame: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30",
  Developer: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  Publisher: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  Genre: "bg-red-500/20 text-red-300 border-red-500/30",
  Platform: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  Character: "bg-pink-500/20 text-pink-300 border-pink-500/30",
  Franchise: "bg-violet-500/20 text-violet-300 border-violet-500/30",
  Award: "bg-orange-500/20 text-orange-300 border-orange-500/30",
};

function extractLabel(uri: string): string {
  if (!uri || !uri.startsWith("http")) return uri || "—";
  const fragment = uri.split("#").pop() || uri.split("/").pop() || uri;
  return decodeURIComponent(fragment).replace(/_/g, " ");
}

function isUri(value: string | null): boolean {
  return !!value && value.startsWith("http://www.videogame-ontology.org/");
}

export function ResultList({
  results,
  totalRows,
  onNodeClick,
}: ResultListProps) {
  if (!results.length) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-lg">Nessun risultato trovato</p>
        <p className="text-sm mt-1">Prova a riformulare la domanda</p>
      </div>
    );
  }

  const columns = Object.keys(results[0]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between px-1">
        <h3 className="text-sm font-medium text-gray-400">
          {totalRows} risultat{totalRows === 1 ? "o" : "i"} trovati
        </h3>
      </div>

      <div className="space-y-2 max-h-[calc(100vh-320px)] overflow-y-auto pr-1">
        {results.map((row, i) => (
          <div
            key={i}
            className="bg-gray-900/80 border border-gray-800 rounded-xl p-4 hover:border-gray-600 transition-all animate-fade-in"
            style={{ animationDelay: `${i * 50}ms` }}
          >
            <div className="grid grid-cols-1 gap-2">
              {columns.map((col) => {
                const value = row[col];
                if (!value) return null;

                const isLink = isUri(value);
                const displayValue = isLink ? extractLabel(value) : value;

                return (
                  <div key={col} className="flex items-start gap-2">
                    <span className="text-xs text-gray-500 uppercase tracking-wide min-w-[100px] pt-0.5">
                      {col}
                    </span>
                    {isLink ? (
                      <button
                        onClick={() => onNodeClick(value)}
                        className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors flex items-center gap-1 text-left"
                      >
                        {displayValue}
                        <ExternalLink className="w-3 h-3 flex-shrink-0" />
                      </button>
                    ) : (
                      <span className="text-sm text-gray-200 text-left">
                        {displayValue}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
