"use client";

import { useCallback, useEffect, useState } from "react";

/** Load one API resource; re-runs when any of `deps` changes; `retry` loads it again. */
export function useData<T>(load: () => Promise<T>, deps: unknown[] = []): {
  data: T | null;
  error: string | null;
  retry: () => void;
} {
  const [state, setState] = useState<{ data: T | null; error: string | null }>({ data: null, error: null });
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  useEffect(() => {
    let live = true;
    setState((s) => ({ data: s.data, error: null }));
    load().then(
      (data) => live && setState({ data, error: null }),
      (e: Error) => live && setState({ data: null, error: e.message }),
    );
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, attempt]);
  return { ...state, retry };
}
