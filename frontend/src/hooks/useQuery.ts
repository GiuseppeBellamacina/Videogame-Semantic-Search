import { useState, useCallback, useRef } from "react";
import type { BuilderRequest, QueryResponse, SearchProgress } from "@/types";
import { runBuilderQuery, streamQuery } from "@/lib/api";
import { getCached, setCached, hasCached } from "@/lib/queryCache";

export function useQuery() {
  const [data, setData] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<SearchProgress | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const begin = () => {
    abortRef.current?.abort();
    const c = new AbortController();
    abortRef.current = c;
    setData(null);
    setError(null);
    setProgress(null);
    setLoading(true);
    return c;
  };

  const search = useCallback(async (question: string) => {
    const key = question.trim();
    if (hasCached(key)) {
      abortRef.current?.abort();
      setError(null);
      setProgress(null);
      setLoading(false);
      setData(getCached(key)!);
      return;
    }
    const c = begin();
    try {
      await streamQuery(
        key,
        (e) => {
          if (e.type === "phase")
            setProgress((p) => ({
              sparql: p?.sparql,
              phase: e.phase,
              attempt: e.attempt ?? p?.attempt ?? 1,
            }));
          else if (e.type === "query")
            setProgress((p) => ({
              phase: p?.phase ?? "generating",
              attempt: p?.attempt ?? 1,
              sparql: e.sparql,
            }));
          else if (e.type === "retry")
            setProgress((p) => ({
              phase: p?.phase ?? "generating",
              attempt: p?.attempt ?? 1,
              sparql: p?.sparql,
              retry: e.reason,
            }));
          else if (e.type === "done") {
            setCached(key, e.result);
            setData(e.result);
          } else if (e.type === "error") setError(e.detail);
        },
        c.signal,
      );
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Errore imprevisto");
    } finally {
      if (!c.signal.aborted) {
        setLoading(false);
        setProgress(null);
      }
    }
  }, []);

  // Query builder: no LLM, a single short request
  const searchBuilder = useCallback(async (body: BuilderRequest) => {
    const c = begin();
    try {
      setData(await runBuilderQuery(body, c.signal));
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Errore imprevisto");
    } finally {
      if (!c.signal.aborted) setLoading(false);
    }
  }, []);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setLoading(false);
    setProgress(null);
  }, []);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
  }, []);

  return { data, loading, error, progress, search, searchBuilder, cancel, reset };
}
