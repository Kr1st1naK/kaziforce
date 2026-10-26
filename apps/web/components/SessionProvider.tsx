"use client";

/**
 * Who is signed in, loaded once and shared.
 *
 * The session lives in an HttpOnly cookie the API sets, so the interface cannot
 * read it directly and asks the API instead. `loading` matters: a guard must not
 * redirect to sign-in before the answer arrives, or a refresh would throw a
 * signed-in person out.
 */

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { Role, Session } from "@/lib/types";

type SessionState = {
  session: Session | null;
  loading: boolean;
  refresh: () => Promise<void>;
  setSession: (session: Session | null) => void;
  signOut: () => Promise<void>;
};

const SessionContext = createContext<SessionState>({
  session: null,
  loading: true,
  refresh: async () => {},
  setSession: () => {},
  signOut: async () => {},
});

export function useSession(): SessionState {
  return useContext(SessionContext);
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const refresh = useCallback(async () => {
    try {
      setSession(await api.session());
    } catch {
      setSession(null); // not signed in, or the API is unreachable
    } finally {
      setLoading(false);
    }
  }, []);

  // Asked once on load. Written out rather than calling refresh(), so the state
  // is only set after the request settles.
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const current = await api.session();
        if (!cancelled) setSession(current);
      } catch {
        if (!cancelled) setSession(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const signOut = useCallback(async () => {
    try {
      await api.signOut();
    } catch {
      /* the session is gone either way */
    }
    setSession(null);
    router.push("/");
  }, [router]);

  return (
    <SessionContext.Provider value={{ session, loading, refresh, setSession, signOut }}>
      {children}
    </SessionContext.Provider>
  );
}

/** Where a signed-in person belongs, given what they own. */
export function homeFor(session: Session): string {
  if (session.account.role === "worker") {
    return session.worker_profile_id ? "/worker/matches" : "/worker/profile";
  }
  return session.postings > 0 ? "/client/postings" : "/client/post";
}

/**
 * Sends anyone who should not be on this page somewhere they should be.
 * Returns true while the answer is still unknown, so the page can hold off rendering.
 */
export function useGuard(role: Role): boolean {
  const { session, loading } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!session) {
      router.replace("/");
    } else if (session.account.role !== role) {
      router.replace(homeFor(session));
    }
  }, [loading, session, role, router]);

  return loading || !session || session.account.role !== role;
}

export function useRedirectIfSignedIn(): void {
  const { session, loading } = useSession();
  const router = useRouter();
  useEffect(() => {
    if (!loading && session) router.replace(homeFor(session));
  }, [loading, session, router]);
}

export function ApiErrorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
}
