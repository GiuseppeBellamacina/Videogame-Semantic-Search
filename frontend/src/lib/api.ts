import type {
  BuilderRequest,
  BuilderSchema,
  GraphLink,
  NodeDetailResponse,
  OntologyStats,
  QueryResponse,
  Suggestion,
} from "@/types";

const API_BASE = `${import.meta.env.VITE_API_URL ?? ""}/api`;

export async function queryOntology(
  question: string,
  signal?: AbortSignal,
): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
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

export async function getCrossLinks(
  existingUris: string[],
  newUris: string[],
): Promise<GraphLink[]> {
  if (newUris.length === 0) return [];
  const res = await fetch(`${API_BASE}/cross-links`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ existing_uris: existingUris, new_uris: newUris }),
  });
  if (!res.ok) return [];
  const data = await res.json();
  return data.links ?? [];
}

export async function suggest(
  q: string,
  types: string,
  signal?: AbortSignal,
): Promise<{ match: string; suggestions: Suggestion[] }> {
  const params = new URLSearchParams({ q });
  if (types) params.set("type", types);
  const res = await fetch(`${API_BASE}/suggest?${params}`, { signal });
  if (!res.ok) return { match: "", suggestions: [] };
  return res.json();
}

export async function getBuilderSchema(): Promise<BuilderSchema> {
  const res = await fetch(`${API_BASE}/builder/schema`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function runBuilderQuery(
  body: BuilderRequest,
  signal?: AbortSignal,
): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/builder/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}
