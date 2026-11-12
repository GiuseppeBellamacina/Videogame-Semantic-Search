import type {
  BuilderRequest,
  BuilderSchema,
  GraphLink,
  SearchEvent,
  NodeDetailResponse,
  OntologyStats,
  QueryResponse,
  Suggestion,
} from "@/types";

const ORIGIN = import.meta.env.VITE_API_URL ?? "";
const API_BASE = `${ORIGIN}/api`;

/** Backend-relative paths (stored images) need the API origin; absolute URLs pass through. */
export const assetUrl = (u: string | null) =>
  u && u.startsWith("/") ? `${ORIGIN}${u}` : u;

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

export async function fetchImages(
  items: { name: string; type: string }[],
  signal?: AbortSignal,
): Promise<Record<string, string | null>> {
  const res = await fetch(`${API_BASE}/images`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
    signal,
  });
  if (!res.ok) return {};
  return (await res.json()).images ?? {};
}

export async function countBuilder(
  filters: BuilderRequest["filters"],
  signal?: AbortSignal,
): Promise<number> {
  const res = await fetch(`${API_BASE}/builder/count`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filters }),
    signal,
  });
  if (!res.ok) return -1;
  return (await res.json()).count ?? 0;
}

/** Natural-language search as a stream of progress events (server-sent events). */
export async function streamQuery(
  question: string,
  onEvent: (e: SearchEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });
  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({ detail: "Errore sconosciuto" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let i: number;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const line = buf.slice(0, i).trim();
      buf = buf.slice(i + 2);
      if (line.startsWith("data:")) onEvent(JSON.parse(line.slice(5)));
    }
  }
}
