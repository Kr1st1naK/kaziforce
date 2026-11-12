/**
 * The profile screen is a form only when there is something to fill in.
 *
 * Once a profile exists it is content to read, and editing is a choice the worker
 * makes. These tests hold that line, and the one below it: cancelling asks before
 * it throws anything away.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Activity } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/worker/profile/page";
import type { OwnContact, Session, Worker } from "@/lib/types";

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

const CONTACT: OwnContact = { first_name: "Amina", last_name: "Wanjiru", consent: true, phone: "712345678" };

function profile(worker: Worker = WORKER, contact: OwnContact = CONTACT) {
  return { worker_id: "w-1", worker, enrichment: { terms: [], occupations: [], unmapped: [] }, contact };
}

function signedIn(workerProfileId: string | null): Session {
  return { account: { account_id: "a-1", phone: "712345678", role: "worker" }, worker_profile_id: workerProfileId, postings: 0 };
}

beforeEach(() => {
  vi.clearAllMocks();
  myProfile.mockResolvedValue(profile());
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
    updateMyProfile.mockResolvedValue(profile(edited));

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

describe("a worker's name and who can see it", () => {
  beforeEach(() => {
    session = signedIn("w-1");
  });

  it("reads their name and says clients can see it, with the number they will see", async () => {
    render(<Page />);
    expect(await screen.findByText("Amina Wanjiru")).toBeVisible();
    expect(screen.getByText(/clients who post a job in your trade can see your name and your number, \+254 712 345 678/i)).toBeVisible();
  });

  it("says plainly when they are hidden", async () => {
    myProfile.mockResolvedValue(profile(WORKER, { ...CONTACT, consent: false }));
    render(<Page />);
    expect(await screen.findByText(/Your name and number are hidden from clients/)).toBeVisible();
  });

  it("edits the name and the agreement in the same form as the rest", async () => {
    render(<Page />);
    await userEvent.click(await screen.findByRole("button", { name: "Edit profile" }));
    expect(screen.getByLabelText(/^First name/)).toHaveValue("Amina");
    expect(screen.getByLabelText(/^Last name/)).toHaveValue("Wanjiru");
    expect(screen.getByRole("checkbox", { name: /can see my name and phone number/ })).toBeChecked();
  });

  it("turns the agreement off, sends it, and shows the profile hidden", async () => {
    updateMyProfile.mockResolvedValue(profile(WORKER, { ...CONTACT, consent: false }));
    render(<Page />);
    await userEvent.click(await screen.findByRole("button", { name: "Edit profile" }));
    await userEvent.click(screen.getByRole("checkbox", { name: /can see my name and phone number/ }));
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => expect(updateMyProfile).toHaveBeenCalledTimes(1));
    expect(updateMyProfile).toHaveBeenCalledWith(
      expect.objectContaining({ first_name: "Amina", last_name: "Wanjiru", contact_consent: false }),
    );
    expect(await screen.findByText(/Your name and number are hidden from clients/)).toBeVisible();
  });

  it("edits the name and sends it tidied", async () => {
    updateMyProfile.mockResolvedValue(profile(WORKER, { ...CONTACT, first_name: "Aminata" }));
    render(<Page />);
    await userEvent.click(await screen.findByRole("button", { name: "Edit profile" }));
    const first = screen.getByLabelText(/^First name/);
    await userEvent.clear(first);
    await userEvent.type(first, "  Aminata ");
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => expect(updateMyProfile).toHaveBeenCalled());
    expect(updateMyProfile).toHaveBeenCalledWith(expect.objectContaining({ first_name: "Aminata", last_name: "Wanjiru" }));
    expect(await screen.findByText("Aminata Wanjiru")).toBeVisible();
  });

  it("refuses an invalid name before it is sent", async () => {
    render(<Page />);
    await userEvent.click(await screen.findByRole("button", { name: "Edit profile" }));
    const first = screen.getByLabelText(/^First name/);
    await userEvent.clear(first);
    await userEvent.type(first, "Am1na");
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByText("Use letters, spaces, hyphens and apostrophes only.")).toBeVisible();
    expect(updateMyProfile).not.toHaveBeenCalled();
  });

  it("will not share an account that has no name, and says why", async () => {
    myProfile.mockResolvedValue(profile(WORKER, { first_name: null, last_name: null, consent: false, phone: "712345678" }));
    render(<Page />);
    expect(await screen.findByText("Not added yet")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Edit profile" }));
    await userEvent.click(screen.getByRole("checkbox", { name: /can see my name and phone number/ }));
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByText("Add your first and last name before sharing them.")).toBeVisible();
    expect(updateMyProfile).not.toHaveBeenCalled();
  });

  it("lets an account with no name save the rest of its profile, sending no name", async () => {
    myProfile.mockResolvedValue(profile(WORKER, { first_name: null, last_name: null, consent: false, phone: "712345678" }));
    updateMyProfile.mockResolvedValue(profile(WORKER, { first_name: null, last_name: null, consent: false, phone: "712345678" }));
    render(<Page />);
    await userEvent.click(await screen.findByRole("button", { name: "Edit profile" }));
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => expect(updateMyProfile).toHaveBeenCalledTimes(1));
    const sent = updateMyProfile.mock.calls[0][0];
    expect(sent).not.toHaveProperty("first_name");
    expect(sent).not.toHaveProperty("contact_consent");
  });

  it("does not ask for a name while there is no profile to attach it to", () => {
    session = signedIn(null);
    render(<Page />);
    expect(screen.queryByLabelText(/^First name/)).toBeNull();
    expect(screen.queryByRole("checkbox")).toBeNull();
  });
});

describe("the submit button after a profile is created", () => {
  it("is ready again when the worker comes back to the page, and does not say Saving…", async () => {
    session = signedIn(null);
    createWorker.mockResolvedValue({});
    const { rerender } = render(
      <Activity mode="visible">
        <Page />
      </Activity>,
    );

    await userEvent.type(screen.getByLabelText(/What work do you do\?/), "electrician");
    await userEvent.type(screen.getByLabelText(/About you/), "Electrical work in houses for three years.");
    await userEvent.selectOptions(screen.getByLabelText(/Where do you work\?/), "Nairobi - Kasarani");
    await userEvent.selectOptions(screen.getByLabelText(/When can you work\?/), "Full-time");
    await userEvent.type(screen.getByLabelText(/Your daily rate/), "2500");
    await userEvent.click(screen.getByRole("button", { name: "Create profile" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/worker/matches"));

    // Next keeps the page mounted, hidden, once it has navigated away, and shows it again on the next visit.
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

    expect(screen.queryByText("Finding your matches…")).not.toBeInTheDocument();
    expect(screen.queryByText("Saving…")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create profile" })).toBeEnabled();
  });
});
