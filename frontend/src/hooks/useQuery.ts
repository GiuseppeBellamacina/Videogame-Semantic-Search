import { useState, useCallback } from "react";
import type { QueryResponse } from "@/types";
import { queryOntology } from "@/lib/api";

export function useQuery() {
  const [data, setData] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (question: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await queryOntology(question);
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
  }, []);

  return { data, loading, error, search, reset };
}
