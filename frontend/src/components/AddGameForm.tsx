import { useState } from "react";
import { addGame } from "@/lib/api";
import type { NewGameData } from "@/lib/api";

interface AddGameFormProps {
  onGameAdded?: () => void;
}

export function AddGameForm({ onGameAdded }: AddGameFormProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [form, setForm] = useState<NewGameData>({
    name: "",
    release_date: "",
    developer: "",
    publisher: "",
    genres: [],
    platforms: [],
    description: "",
  });
  const [genreInput, setGenreInput] = useState("");
  const [platformInput, setPlatformInput] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await addGame({
        ...form,
        genres: form.genres?.length ? form.genres : undefined,
        platforms: form.platforms?.length ? form.platforms : undefined,
        release_date: form.release_date || undefined,
        developer: form.developer || undefined,
        publisher: form.publisher || undefined,
        description: form.description || undefined,
      });
      setSuccess(result.message);
      setForm({
        name: "",
        release_date: "",
        developer: "",
        publisher: "",
        genres: [],
        platforms: [],
        description: "",
      });
      setGenreInput("");
      setPlatformInput("");
      onGameAdded?.();
    } catch (err: any) {
      setError(err.message || "Failed to add game");
    } finally {
      setLoading(false);
    }
  };

  const addGenre = () => {
    if (genreInput.trim() && !form.genres?.includes(genreInput.trim())) {
      setForm({ ...form, genres: [...(form.genres || []), genreInput.trim()] });
      setGenreInput("");
    }
  };

  const addPlatform = () => {
    if (
      platformInput.trim() &&
      !form.platforms?.includes(platformInput.trim())
    ) {
      setForm({
        ...form,
        platforms: [...(form.platforms || []), platformInput.trim()],
      });
      setPlatformInput("");
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="w-full py-2 px-4 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 text-sm font-medium hover:bg-indigo-600/30 transition-colors"
      >
        + Aggiungi gioco
      </button>
    );
  }

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-200">
          Aggiungi nuovo gioco
        </h3>
        <button
          onClick={() => setIsOpen(false)}
          className="text-gray-500 hover:text-gray-300 text-lg"
        >
          ×
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-2">
        <input
          type="text"
          placeholder="Nome del gioco *"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          className="w-full px-3 py-1.5 rounded bg-gray-900 border border-gray-700 text-sm text-gray-200 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
          required
        />

        <input
          type="date"
          placeholder="Data di uscita"
          value={form.release_date}
          onChange={(e) => setForm({ ...form, release_date: e.target.value })}
          className="w-full px-3 py-1.5 rounded bg-gray-900 border border-gray-700 text-sm text-gray-200 focus:border-indigo-500 focus:outline-none"
        />

        <input
          type="text"
          placeholder="Developer"
          value={form.developer}
          onChange={(e) => setForm({ ...form, developer: e.target.value })}
          className="w-full px-3 py-1.5 rounded bg-gray-900 border border-gray-700 text-sm text-gray-200 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
        />

        <input
          type="text"
          placeholder="Publisher"
          value={form.publisher}
          onChange={(e) => setForm({ ...form, publisher: e.target.value })}
          className="w-full px-3 py-1.5 rounded bg-gray-900 border border-gray-700 text-sm text-gray-200 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
        />

        {/* Genres */}
        <div className="space-y-1">
          <div className="flex gap-1">
            <input
              type="text"
              placeholder="Genere"
              value={genreInput}
              onChange={(e) => setGenreInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addGenre();
                }
              }}
              className="flex-1 px-3 py-1.5 rounded bg-gray-900 border border-gray-700 text-sm text-gray-200 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={addGenre}
              className="px-2 py-1.5 rounded bg-gray-700 text-gray-300 text-sm hover:bg-gray-600"
            >
              +
            </button>
          </div>
          {form.genres && form.genres.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {form.genres.map((g) => (
                <span
                  key={g}
                  className="px-2 py-0.5 rounded-full bg-red-500/20 text-red-300 text-xs cursor-pointer hover:bg-red-500/30"
                  onClick={() =>
                    setForm({
                      ...form,
                      genres: form.genres?.filter((x) => x !== g),
                    })
                  }
                >
                  {g} ×
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Platforms */}
        <div className="space-y-1">
          <div className="flex gap-1">
            <input
              type="text"
              placeholder="Piattaforma"
              value={platformInput}
              onChange={(e) => setPlatformInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addPlatform();
                }
              }}
              className="flex-1 px-3 py-1.5 rounded bg-gray-900 border border-gray-700 text-sm text-gray-200 placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={addPlatform}
              className="px-2 py-1.5 rounded bg-gray-700 text-gray-300 text-sm hover:bg-gray-600"
            >
              +
            </button>
          </div>
          {form.platforms && form.platforms.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {form.platforms.map((p) => (
                <span
                  key={p}
                  className="px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 text-xs cursor-pointer hover:bg-blue-500/30"
                  onClick={() =>
                    setForm({
                      ...form,
                      platforms: form.platforms?.filter((x) => x !== p),
                    })
                  }
                >
                  {p} ×
                </span>
              ))}
            </div>
          )}
        </div>

        <textarea
          placeholder="Descrizione"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          className="w-full px-3 py-1.5 rounded bg-gray-900 border border-gray-700 text-sm text-gray-200 placeholder-gray-500 focus:border-indigo-500 focus:outline-none resize-none"
          rows={2}
        />

        {error && <p className="text-xs text-red-400">{error}</p>}
        {success && <p className="text-xs text-emerald-400">{success}</p>}

        <button
          type="submit"
          disabled={loading || !form.name.trim()}
          className="w-full py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "Aggiunta in corso..." : "Aggiungi gioco"}
        </button>
      </form>
    </div>
  );
}
