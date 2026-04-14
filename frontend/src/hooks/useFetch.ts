import { useState, useEffect, useRef, useCallback } from "react";

export function useFetch<T>(fetcher: () => Promise<T>, deps: unknown[] = [], refreshInterval?: number) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refetch = useCallback(() => {
    return fetcherRef.current().then((result) => {
      setData(result);
      setError(null);
      return result;
    }).catch((err) => {
      setError(err.message);
    });
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetcherRef.current()
      .then((result) => {
        if (!cancelled) { setData(result); setError(null); }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  // Auto-Refresh
  useEffect(() => {
    if (!refreshInterval) return;
    const interval = setInterval(() => {
      fetcherRef.current()
        .then((result) => { setData(result); setError(null); })
        .catch(() => {});
    }, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  return { data, loading, error, refetch };
}
