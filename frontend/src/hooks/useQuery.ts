import { useState, useCallback, useRef } from "react";
import type { QueryResponse } from "@/types";
import { queryOntology } from "@/lib/api";
import { getCached, setCached, hasCached } from "@/lib/queryCache";

export function useQuery() {
  const [data, setData] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const search = useCallback(async (question: string) => {
    const key = question.trim();

    // Return cached result immediately without loading state
    if (hasCached(key)) {
      abortControllerRef.current?.abort();
      setData(getCached(key)!);
      setError(null);
      setLoading(false);
      return;
    }

    // Cancel any in-flight request
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setError(null);

    try {
      const response = await queryOntology(key, controller.signal);
      setCached(key, response);
      setData(response);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : "An error occurred");
      setData(null);
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  }, []);

  const cancel = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setLoading(false);
  }, []);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
  }, []);

  return { data, loading, error, search, cancel, reset };
}
