import { useEffect, useState } from "react";
import { X, Loader2, ExternalLink, ArrowRight, ArrowLeft } from "lucide-react";
import type { NodeDetails } from "@/types";
import { getNodeDetails } from "@/lib/api";

interface NodeDetailProps {
  uri: string | null;
  onClose: () => void;
  onNavigate: (uri: string) => void;
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

export function NodeDetail({ uri, onClose, onNavigate }: NodeDetailProps) {
  const [details, setDetails] = useState<NodeDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!uri) {
      setDetails(null);
      return;
    }

    setLoading(true);
    setError(null);

    getNodeDetails(uri)
      .then((res) => setDetails(res.details))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [uri]);

  if (!uri) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-gray-900 border-l border-gray-700 shadow-2xl z-50 animate-slide-in overflow-y-auto">
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
            {/* Type badge */}
            <div className="flex items-center gap-2">
              <span
                className={`px-3 py-1 rounded-full text-xs font-medium ${
                  TYPE_BADGES[details.type] || "bg-gray-700 text-gray-300"
                }`}
              >
                {details.type}
              </span>
            </div>

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

            {/* Outgoing relations */}
            {details.outgoing_relations.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide flex items-center gap-1">
                  <ArrowRight className="w-3.5 h-3.5" />
                  Relazioni in uscita ({details.outgoing_relations.length})
                </h3>
                <div className="space-y-1.5">
                  {details.outgoing_relations.map((rel, i) => (
                    <button
                      key={i}
                      onClick={() => onNavigate(rel.target_uri)}
                      className="w-full flex items-center gap-2 bg-gray-800/50 hover:bg-gray-800 rounded-lg p-2.5 transition-colors text-left group"
                    >
                      <span className="text-xs text-gray-500 min-w-[80px]">
                        {rel.predicate}
                      </span>
                      <span className="text-sm text-indigo-400 group-hover:text-indigo-300 truncate flex-1">
                        {rel.target_label}
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded ${
                          TYPE_BADGES[rel.target_type] ||
                          "bg-gray-700 text-gray-400"
                        }`}
                      >
                        {rel.target_type}
                      </span>
                      <ExternalLink className="w-3 h-3 text-gray-600 group-hover:text-gray-400 flex-shrink-0" />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Incoming relations */}
            {details.incoming_relations.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide flex items-center gap-1">
                  <ArrowLeft className="w-3.5 h-3.5" />
                  Relazioni in entrata ({details.incoming_relations.length})
                </h3>
                <div className="space-y-1.5">
                  {details.incoming_relations.slice(0, 20).map((rel, i) => (
                    <button
                      key={i}
                      onClick={() => onNavigate(rel.source_uri)}
                      className="w-full flex items-center gap-2 bg-gray-800/50 hover:bg-gray-800 rounded-lg p-2.5 transition-colors text-left group"
                    >
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded ${
                          TYPE_BADGES[rel.source_type] ||
                          "bg-gray-700 text-gray-400"
                        }`}
                      >
                        {rel.source_type}
                      </span>
                      <span className="text-sm text-indigo-400 group-hover:text-indigo-300 truncate flex-1">
                        {rel.source_label}
                      </span>
                      <span className="text-xs text-gray-500">
                        {rel.predicate}
                      </span>
                      <ExternalLink className="w-3 h-3 text-gray-600 group-hover:text-gray-400 flex-shrink-0" />
                    </button>
                  ))}
                  {details.incoming_relations.length > 20 && (
                    <p className="text-xs text-gray-500 text-center py-1">
                      ...e {details.incoming_relations.length - 20} altre
                    </p>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
