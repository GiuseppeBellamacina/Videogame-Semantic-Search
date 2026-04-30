import { useState } from "react";
import { Search, Sparkles, Loader2 } from "lucide-react";

interface SearchBarProps {
  onSearch: (query: string) => void;
  loading: boolean;
}

const SUGGESTIONS = [
  "Quali giochi ha sviluppato FromSoftware?",
  "Top 10 giochi con il punteggio Metacritic più alto",
  "Giochi RPG usciti nel 2023",
  "Giochi della serie Zelda",
  "Quali giochi sono disponibili su PlayStation 5?",
  "Giochi sviluppati da Nintendo dopo il 2020",
];

export function SearchBar({ onSearch, loading }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !loading) {
      onSearch(query.trim());
      setShowSuggestions(false);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
    onSearch(suggestion);
    setShowSuggestions(false);
  };

  return (
    <div className="relative w-full">
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative flex items-center">
          <div className="absolute left-4 text-gray-400">
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
            ) : (
              <Search className="w-5 h-5" />
            )}
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            placeholder="Cerca videogiochi in linguaggio naturale..."
            className="w-full pl-12 pr-32 py-4 bg-gray-900 border border-gray-700 rounded-2xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all text-lg"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="absolute right-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-xl font-medium transition-all flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4" />
            Cerca
          </button>
        </div>
      </form>

      {/* Suggestions dropdown */}
      {showSuggestions && !loading && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl overflow-hidden z-50 animate-fade-in">
          <div className="px-4 py-2 text-xs text-gray-500 uppercase tracking-wide border-b border-gray-800">
            Suggerimenti
          </div>
          {SUGGESTIONS.map((suggestion, i) => (
            <button
              key={i}
              onClick={() => handleSuggestionClick(suggestion)}
              className="w-full px-4 py-3 text-left text-gray-300 hover:bg-gray-800 hover:text-white transition-colors flex items-center gap-3"
            >
              <Search className="w-4 h-4 text-gray-500 flex-shrink-0" />
              <span className="text-sm">{suggestion}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
