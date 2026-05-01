import type { NodeDetailResponse, OntologyStats, QueryResponse } from "@/types";

const API_BASE = `${import.meta.env.VITE_API_URL ?? ""}/api`;

export async function queryOntology(question: string): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export async function getNodeDetails(uri: string): Promise<NodeDetailResponse> {
  const encoded = encodeURIComponent(uri);
  const res = await fetch(`${API_BASE}/node/${encoded}`);

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return res.json();
}

export async function getStats(): Promise<OntologyStats> {
  const res = await fetch(`${API_BASE}/stats`);

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return res.json();
}

export async function searchGameImage(
  name: string,
): Promise<{ imageUrl: string | null; source: string | null }> {
  const res = await fetch(
    `${API_BASE}/image-search?name=${encodeURIComponent(name)}`,
  );

  if (!res.ok) {
    return { imageUrl: null, source: null };
  }

  return res.json();
}

export interface NewGameData {
  name: string;
  release_date?: string;
  developer?: string;
  publisher?: string;
  genres?: string[];
  platforms?: string[];
  description?: string;
}

export async function addGame(
  game: NewGameData,
): Promise<{ success: boolean; message: string; uri: string }> {
  const res = await fetch(`${API_BASE}/games`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(game),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export async function listGames(): Promise<{
  games: { uri: string; name: string }[];
  total: number;
}> {
  const res = await fetch(`${API_BASE}/games`);

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return res.json();
}
