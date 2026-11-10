import { useState } from "react";
import { Search, Sparkles, Loader2, X } from "lucide-react";
import { SUGGESTIONS } from "@/lib/queryCache";
import { SuggestInput } from "@/components/SuggestInput";

interface SearchBarProps {
  onSearch: (query: string) => void;
  onCancel: () => void;
  loading: boolean;
}

export function SearchBar({ onSearch, onCancel, loading }: SearchBarProps) {
  const [query, setQuery] = useState("");

  const submit = (q: string = query) => {
    if (q.trim() && !loading) onSearch(q.trim());
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      className="relative"
    >
      <div className="relative flex items-center">
        <div className="absolute left-4 text-gray-400 z-10">
          {loading ? (
            <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
          ) : (
            <Search className="w-5 h-5" />
          )}
        </div>
        <SuggestInput
          value={query}
          onChange={setQuery}
          examples={SUGGESTIONS}
          onSubmit={() => submit()}
          placeholder="Cerca... (scrivi un gioco, uno studio, un genere)"
          disabled={loading}
          className="w-full pl-12 pr-28 sm:pr-32 py-3 sm:py-4 bg-gray-900 border border-gray-700 rounded-2xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all text-base sm:text-lg"
        />
        {loading ? (
          <button
            type="button"
            onClick={onCancel}
            className="absolute right-2 px-6 py-2.5 bg-red-600 hover:bg-red-500 text-white rounded-xl font-medium transition-all flex items-center gap-2"
          >
            <X className="w-4 h-4" />
            Annulla
          </button>
        ) : (
          <button
            type="submit"
            disabled={!query.trim()}
            className="absolute right-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-xl font-medium transition-all flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4" />
            Cerca
          </button>
        )}
      </div>
    </form>
  );
}
