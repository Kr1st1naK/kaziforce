/**
 * Sign in: the way back to the landing page, and a button that does not say "Signing in…" when
 * nothing has been submitted.
 *
 * Next keeps a route it has navigated away from mounted but hidden (an Activity), so that going back is
 * instant. State survives that, including the busy flag: the first usability sessions saw "Signing in…"
 * with disabled fields on a sign-in page nobody had submitted.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Activity } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/sign-in/page";
import { ApiError, NETWORK_MESSAGE } from "@/lib/api";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace, back: vi.fn() }),
  usePathname: () => "/sign-in",
}));

const signIn = vi.fn();
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  api: { signIn: (input: unknown) => signIn(input) },
}));

vi.mock("@/components/SessionProvider", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/SessionProvider")>()),
  useRedirectIfSignedIn: () => {},
  useSession: () => ({ session: null, loading: false, refresh: vi.fn(), setSession: vi.fn(), signOut: vi.fn() }),
}));

const SESSION = { account: { account_id: "a-1", phone: "700000101", role: "worker" }, worker_profile_id: "w-1", postings: 0 };

async function submitValidForm() {
  await userEvent.type(screen.getByLabelText("Phone number"), "700000101");
  const boxes = screen.getAllByLabelText(/^4-digit PIN, digit/);
  for (const [index, digit] of [..."4821"].entries()) await userEvent.type(boxes[index], digit);
  await userEvent.click(screen.getByRole("button", { name: "Continue" }));
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("the way back", () => {
  it("links to the landing page", () => {
    render(<Page />);

    expect(screen.getByRole("link", { name: /Back to the home page/ })).toHaveAttribute("href", "/");
  });
});

describe("the submit button", () => {
  it("says Continue, enabled, when nothing has been submitted", () => {
    render(<Page />);

    expect(screen.getByRole("button", { name: "Continue" })).toBeEnabled();
  });

  it("says Signing in… while a sign-in is in flight", async () => {
    signIn.mockReturnValue(new Promise(() => {}));
    render(<Page />);

    await submitValidForm();

    expect(await screen.findByRole("button", { name: "Signing in…" })).toBeDisabled();
  });

  it("is ready again when the worker returns to the page after a successful sign-in", async () => {
    signIn.mockResolvedValue(SESSION);
    const { rerender } = render(
      <Activity mode="visible">
        <Page />
      </Activity>,
    );

    await submitValidForm();
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/worker/matches"));

    // Next hides the route it navigated away from, and shows it again on the next visit.
    rerender(
      <Activity mode="hidden">
        <Page />
      </Activity>,
    );
    rerender(
      <Activity mode="visible">
        <Page />
      </Activity>,
    );

    expect(screen.getByRole("button", { name: "Continue" })).toBeEnabled();
    expect(screen.queryByText("Signing in…")).not.toBeInTheDocument();
  });
});

describe("when the service cannot be reached", () => {
  it("says so plainly, and Try again sends the same details once more", async () => {
    signIn.mockRejectedValueOnce(new ApiError(0, "network_error", NETWORK_MESSAGE)).mockResolvedValueOnce(SESSION);
    render(<Page />);

    await submitValidForm();
    expect(await screen.findByRole("alert")).toHaveTextContent("We couldn't reach the service. Check your connection and try again.");
    expect(screen.getByRole("alert")).not.toHaveTextContent(/API|running/);

    await userEvent.click(screen.getByRole("button", { name: "Try again" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/worker/matches"));
    expect(signIn).toHaveBeenCalledTimes(2);
    expect(signIn).toHaveBeenLastCalledWith({ phone: "700000101", pin: "4821" });
  });

  it("offers no Try again for an error the server answered, such as a wrong PIN", async () => {
    signIn.mockRejectedValue(new ApiError(401, "invalid_credentials" as never, "That phone number and PIN do not match."));
    render(<Page />);

    await submitValidForm();

    expect(await screen.findByRole("alert")).toHaveTextContent("do not match");
    expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
  });
});
