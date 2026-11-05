/**
 * Nothing to match against means nothing to wait for.
 *
 * A worker with no profile used to land on "Your matches" and read "Finding jobs
 * that suit you…" for as long as they cared to look: the request is never made,
 * because the API has nothing to rank. The screen asks for a profile instead.
 */

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/worker/matches/page";
import type { Session } from "@/lib/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/worker/matches",
}));

const myMatches = vi.fn();
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  api: { myMatches: (k: number) => myMatches(k) },
}));

let session: Session | null = null;
vi.mock("@/components/SessionProvider", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/SessionProvider")>()),
  useGuard: () => false,
  useSession: () => ({ session, loading: false, refresh: vi.fn(), setSession: vi.fn(), signOut: vi.fn() }),
}));

vi.mock("@/components/AppShell", () => ({ AppShell: ({ children }: { children: React.ReactNode }) => <>{children}</> }));

function signedIn(workerProfileId: string | null): Session {
  return { account: { account_id: "a-1", phone: "712345678", role: "worker" }, worker_profile_id: workerProfileId, postings: 0 };
}

beforeEach(() => {
  vi.clearAllMocks();
  myMatches.mockReturnValue(new Promise(() => {}));
});

describe("before a profile exists", () => {
  beforeEach(() => {
    session = signedIn(null);
  });

  it("asks for a profile instead of showing matches that are not coming", () => {
    render(<Page />);

    expect(screen.getByRole("heading", { name: "Create your profile first" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Your matches" })).toBeNull();
    expect(screen.queryByText(/Finding jobs that suit you/)).toBeNull();
    expect(myMatches).not.toHaveBeenCalled();
  });

  it("offers the way to the profile form", () => {
    render(<Page />);

    expect(screen.getByRole("link", { name: "Create your profile" })).toHaveAttribute("href", "/worker/profile");
  });
});

describe("once a profile exists", () => {
  beforeEach(() => {
    session = signedIn("w-1");
  });

  it("shows the matches heading and asks the engine to rank", () => {
    render(<Page />);

    expect(screen.getByRole("heading", { name: "Your matches" })).toBeVisible();
    expect(screen.getByText(/Finding jobs that suit you/)).toBeVisible();
    expect(myMatches).toHaveBeenCalledTimes(1);
  });
});
