/**
 * The posting form starts empty every time.
 *
 * Next keeps this route mounted after the client is sent to the confirmation
 * screen, so a form that is not cleared on success still holds the last posting
 * when they come back to write the next one. Cancel asks before clearing.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/client/post/page";
import { ApiError, NETWORK_MESSAGE } from "@/lib/api";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/client/post",
}));

const createJob = vi.fn();
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  api: { createJob: (input: unknown) => createJob(input) },
}));

vi.mock("@/components/SessionProvider", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/SessionProvider")>()),
  useGuard: () => false,
  useSession: () => ({ session: null, loading: false, refresh: vi.fn(), setSession: vi.fn(), signOut: vi.fn() }),
}));

vi.mock("@/components/AppShell", () => ({ AppShell: ({ children }: { children: React.ReactNode }) => <>{children}</> }));

const fields = () => ({
  title: screen.getByLabelText(/Job title/),
  skills: screen.getByLabelText(/What skills does this job need\?/),
  description: screen.getByLabelText(/Description/),
  budget: screen.getByLabelText(/Budget per day/),
  location: screen.getByLabelText(/Where is the job\?/),
});

async function fillIn() {
  const form = fields();
  await userEvent.type(form.title, "Install a new distribution board");
  await userEvent.type(form.skills, "three-phase distribution board installation");
  await userEvent.type(form.description, "A new board for a three-bedroom house in Kasarani.");
  await userEvent.type(form.budget, "2800");
  await userEvent.selectOptions(form.location, "Nairobi - Kasarani");
}

beforeEach(() => vi.clearAllMocks());

describe("after a job is posted", () => {
  it("leaves the form empty for the next posting", async () => {
    createJob.mockResolvedValue({ posting_id: "p-1" });

    render(<Page />);
    await fillIn();
    await userEvent.click(screen.getByRole("button", { name: /Post job/ }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/client/postings/p-1"));
    const form = fields();
    expect(form.title).toHaveValue("");
    expect(form.skills).toHaveValue("");
    expect(form.description).toHaveValue("");
    expect(form.budget).toHaveValue(null);
    expect(form.location).toHaveValue("");
  });

  it("keeps what was typed when the posting failed, so it is not retyped", async () => {
    createJob.mockRejectedValue(new Error("network"));

    render(<Page />);
    await fillIn();
    await userEvent.click(screen.getByRole("button", { name: /Post job/ }));

    await screen.findByRole("alert");
    expect(fields().title).toHaveValue("Install a new distribution board");
  });
});

describe("cancel on the posting form", () => {
  it("asks first, and changes nothing on No", async () => {
    render(<Page />);
    await fillIn();

    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.getByRole("alertdialog", { name: "Clear this form?" })).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "No, keep it" }));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(fields().title).toHaveValue("Install a new distribution board");
    expect(createJob).not.toHaveBeenCalled();
  });

  it("clears the form on Yes", async () => {
    render(<Page />);
    await fillIn();

    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await userEvent.click(screen.getByRole("button", { name: "Yes, clear it" }));

    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(fields().title).toHaveValue("");
    expect(fields().location).toHaveValue("");
  });
});

describe("when the service cannot be reached", () => {
  it("offers Try again, which posts the same job once more", async () => {
    createJob.mockRejectedValueOnce(new ApiError(0, "network_error", NETWORK_MESSAGE)).mockResolvedValueOnce({ posting_id: "p-9" });
    render(<Page />);
    await fillIn();
    await userEvent.click(screen.getByRole("button", { name: /Post job/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent("We couldn't reach the service");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/client/postings/p-9"));
    expect(createJob).toHaveBeenCalledTimes(2);
    expect(createJob.mock.calls[1][0]).toEqual(createJob.mock.calls[0][0]);
  });
});
