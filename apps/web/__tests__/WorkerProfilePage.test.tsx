/**
 * The profile screen is a form only when there is something to fill in.
 *
 * Once a profile exists it is content to read, and editing is a choice the worker
 * makes. These tests hold that line, and the one below it: cancelling asks before
 * it throws anything away.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/worker/profile/page";
import type { Session, Worker } from "@/lib/types";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/worker/profile",
}));

const myProfile = vi.fn();
const updateMyProfile = vi.fn();
const createWorker = vi.fn();
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  api: {
    myProfile: () => myProfile(),
    updateMyProfile: (input: unknown) => updateMyProfile(input),
    createWorker: (input: unknown) => createWorker(input),
  },
}));

let session: Session | null = null;
vi.mock("@/components/SessionProvider", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/SessionProvider")>()),
  useGuard: () => false,
  useSession: () => ({ session, loading: false, refresh: vi.fn(), setSession: vi.fn(), signOut: vi.fn() }),
}));

vi.mock("@/components/AppShell", () => ({ AppShell: ({ children }: { children: React.ReactNode }) => <>{children}</> }));

const WORKER: Worker = {
  worker_id: "w-1",
  biography: "Experienced electrician with eight years in residential installations.",
  skills: ["fundi wa umeme", "wiring"],
  location: "Nairobi - Kasarani",
  availability: "Full-time",
  rate_expectation: 2500,
};

function signedIn(workerProfileId: string | null): Session {
  return { account: { account_id: "a-1", phone: "712345678", role: "worker" }, worker_profile_id: workerProfileId, postings: 0 };
}

beforeEach(() => {
  vi.clearAllMocks();
  myProfile.mockResolvedValue({ worker_id: "w-1", worker: WORKER, enrichment: { terms: [], occupations: [], unmapped: [] } });
});

describe("a worker who already has a profile", () => {
  beforeEach(() => {
    session = signedIn("w-1");
  });

  it("reads their saved profile rather than a form", async () => {
    render(<Page />);

    expect(await screen.findByText("Experienced electrician with eight years in residential installations.")).toBeVisible();
    expect(screen.getByText("fundi wa umeme")).toBeVisible();
    expect(screen.getByText("Nairobi - Kasarani")).toBeVisible();
    expect(screen.getByText("Full-time")).toBeVisible();
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(screen.getByRole("button", { name: "Edit profile" })).toBeVisible();
  });

  it("turns into the form on Edit, prefilled with what was saved", async () => {
    render(<Page />);
    await userEvent.click(await screen.findByRole("button", { name: "Edit profile" }));

    expect(screen.getByLabelText(/What work do you do\?/)).toHaveValue("fundi wa umeme, wiring");
    expect(screen.getByLabelText(/Where do you work\?/)).toHaveValue("Nairobi - Kasarani");
    expect(screen.getByRole("button", { name: "Save changes" })).toBeVisible();
  });

  it("saves the changes and goes back to reading them", async () => {
    const edited = { ...WORKER, biography: "Now also doing solar installations." };
    updateMyProfile.mockResolvedValue({ worker_id: "w-1", worker: edited, enrichment: {} });

    render(<Page />);
    await userEvent.click(await screen.findByRole("button", { name: "Edit profile" }));

    const about = screen.getByLabelText(/About you/);
    await userEvent.clear(about);
    await userEvent.type(about, "Now also doing solar installations.");
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => expect(updateMyProfile).toHaveBeenCalledTimes(1));
    expect(updateMyProfile).toHaveBeenCalledWith(
      expect.objectContaining({ biography: "Now also doing solar installations.", location: "Nairobi - Kasarani" }),
    );
    expect(await screen.findByRole("button", { name: "Edit profile" })).toBeVisible();
    expect(screen.getByText("Now also doing solar installations.")).toBeVisible();
    // Saving an edit must never create a second profile.
    expect(createWorker).not.toHaveBeenCalled();
  });

  it("puts back what was saved when an edit is cancelled and confirmed", async () => {
    render(<Page />);
    await userEvent.click(await screen.findByRole("button", { name: "Edit profile" }));

    const about = screen.getByLabelText(/About you/);
    await userEvent.clear(about);
    await userEvent.type(about, "Typed by mistake.");
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.getByRole("alertdialog", { name: "Discard your changes?" })).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Yes, discard them" }));

    expect(await screen.findByRole("button", { name: "Edit profile" })).toBeVisible();
    expect(screen.getByText("Experienced electrician with eight years in residential installations.")).toBeVisible();
    expect(updateMyProfile).not.toHaveBeenCalled();
  });
});

describe("a worker who has no profile yet", () => {
  beforeEach(() => {
    session = signedIn(null);
  });

  it("gets the form straight away, with nothing to edit into", () => {
    render(<Page />);

    expect(screen.getByRole("heading", { name: "Create your worker profile" })).toBeVisible();
    expect(screen.getByLabelText(/What work do you do\?/)).toHaveValue("");
    expect(screen.queryByRole("button", { name: "Edit profile" })).toBeNull();
    expect(myProfile).not.toHaveBeenCalled();
  });

  it("asks before clearing the form, and leaves it alone on No", async () => {
    render(<Page />);
    const skills = screen.getByLabelText(/What work do you do\?/);
    await userEvent.type(skills, "fundi wa umeme");

    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.getByRole("alertdialog", { name: "Clear this form?" })).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "No, keep it" }));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(skills).toHaveValue("fundi wa umeme");
  });

  it("clears the form on Yes", async () => {
    render(<Page />);
    const skills = screen.getByLabelText(/What work do you do\?/);
    await userEvent.type(skills, "fundi wa umeme");
    await userEvent.selectOptions(screen.getByLabelText(/Where do you work\?/), "Nairobi - Kasarani");

    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await userEvent.click(screen.getByRole("button", { name: "Yes, clear it" }));

    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(skills).toHaveValue("");
    expect(screen.getByLabelText(/Where do you work\?/)).toHaveValue("");
  });
});
