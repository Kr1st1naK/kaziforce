"use client";

/**
 * Engine readiness, shown once in the layout.
 *
 * The API loads its model and job embeddings for about half a minute after the
 * server starts and answers 503 until then (docs/api.md). This polls /health
 * until it is ready and then stops. AppShell draws the notice; forms stay
 * usable throughout, because the API client waits out a 503 by itself.
 */

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

const POLL_INTERVAL_MS = 3000;

export type EngineState = {
  ready: boolean;
  candidateJobs: number | null;
  unreachable: boolean;
  recheck: () => void;
};

const EngineStatusContext = createContext<EngineState>({
  ready: false,
  candidateJobs: null,
  unreachable: false,
  recheck: () => {},
});

export function useEngineStatus(): EngineState {
  return useContext(EngineStatusContext);
}

export function EngineStatusProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [candidateJobs, setCandidateJobs] = useState<number | null>(null);
  const [unreachable, setUnreachable] = useState(false);
  const [attempt, setAttempt] = useState(0);

  const recheck = useCallback(() => setAttempt((n) => n + 1), []);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const poll = async () => {
      try {
        const health = await api.health();
        if (cancelled) return;
        setUnreachable(false);
        setReady(health.ready);
        setCandidateJobs(health.candidate_jobs);
        if (!health.ready) timer = setTimeout(poll, POLL_INTERVAL_MS);
      } catch {
        if (cancelled) return;
        setUnreachable(true);
        setReady(false);
        timer = setTimeout(poll, POLL_INTERVAL_MS);
      }
    };

    void poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [attempt]);

  return (
    <EngineStatusContext.Provider value={{ ready, candidateJobs, unreachable, recheck }}>
      {children}
    </EngineStatusContext.Provider>
  );
}
