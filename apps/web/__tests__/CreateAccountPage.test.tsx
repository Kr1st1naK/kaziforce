/**
 * Account creation: the number the numbering plan allows, and a confirmation PIN
 * that is typed rather than filled in for the person.
 *
 * Prefilling the second PIN would confirm a typo against itself, so the screen
 * keeps both fields and says as soon as they differ.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/create-account/page";

let query = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/create-account",
  useSearchParams: () => new URLSearchParams(query),
}));

const createAccount = vi.fn();
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  api: { createAccount: (input: unknown) => createAccount(input) },
}));

vi.mock("@/components/SessionProvider", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/components/SessionProvider")>()),
  useRedirectIfSignedIn: () => {},
  useSession: () => ({ session: null, loading: false, refresh: vi.fn(), setSession: vi.fn(), signOut: vi.fn() }),
}));

const phoneField = () => screen.getByLabelText("Phone number");
const firstName = () => screen.getByLabelText(/^First name/);
const lastName = () => screen.getByLabelText(/^Last name/);
const consentBox = () => screen.getByRole("checkbox", { name: /can see my name and phone number/ });

async function fillWorkerDetails(first = "Amina", last = "Wanjiru") {
  await userEvent.type(firstName(), first);
  await userEvent.type(lastName(), last);
  await userEvent.click(consentBox());
}

async function typePin(label: RegExp | string, digits: string) {
  const boxes = screen.getAllByLabelText(new RegExp(`^${label}, digit`));
  for (const [index, digit] of [...digits].entries()) {
    await userEvent.type(boxes[index], digit);
  }
}

beforeEach(() => {
  vi.clearAllMocks();
  query = "";
});

describe("the role the landing page chose", () => {
  it.each([
    ["role=worker", "I'm a worker"],
    ["role=client", "I'm a client"],
    ["", "I'm a worker"],
    ["role=admin", "I'm a worker"],
  ])("starts %j with %s selected", (search, label) => {
    query = search;
    render(<Page />);
    expect(screen.getByRole("radio", { name: label })).toBeChecked();
  });
});

describe("the phone number", () => {
  it("shows the digits in blocks of three as they are typed", async () => {
    render(<Page />);
    await userEvent.type(phoneField(), "712345678");
    expect(phoneField()).toHaveValue("712 345 678");
  });

  it("takes no more than the nine digits that follow +254", async () => {
    render(<Page />);
    await userEvent.type(phoneField(), "7123456789999");
    expect(phoneField()).toHaveValue("712 345 678");
  });

  it("refuses a first digit that is not 7 or 1, and does not call the API", async () => {
    render(<Page />);
    await userEvent.type(phoneField(), "312345678");
    await typePin("Create a 4-digit PIN", "4821");
    await typePin("Confirm PIN", "4821");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText(/starts 7 or 1/)).toBeVisible();
    expect(createAccount).not.toHaveBeenCalled();
  });

  it("refuses a number that is short of nine digits", async () => {
    render(<Page />);
    await userEvent.type(phoneField(), "71234567");
    await typePin("Create a 4-digit PIN", "4821");
    await typePin("Confirm PIN", "4821");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText(/all 9 digits/)).toBeVisible();
    expect(createAccount).not.toHaveBeenCalled();
  });

  it("submits a number the plan allows", async () => {
    createAccount.mockResolvedValue({ account: { account_id: "a-1", phone: "712345678", role: "worker" }, worker_profile_id: null, postings: 0 });

    render(<Page />);
    await fillWorkerDetails();
    await userEvent.type(phoneField(), "712345678");
    await typePin("Create a 4-digit PIN", "4821");
    await typePin("Confirm PIN", "4821");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(createAccount).toHaveBeenCalledWith({
      phone: "712345678",
      pin: "4821",
      role: "worker",
      first_name: "Amina",
      last_name: "Wanjiru",
      contact_consent: true,
    });
  });
});

async function submitWorker() {
  await userEvent.type(phoneField(), "712345678");
  await typePin("Create a 4-digit PIN", "4821");
  await typePin("Confirm PIN", "4821");
  await userEvent.click(screen.getByRole("button", { name: "Create account" }));
}

describe("a worker's name and agreement", () => {
  it("asks for a first name, a last name and an agreement, all marked required", () => {
    render(<Page />);
    expect(firstName()).toBeVisible();
    expect(lastName()).toBeVisible();
    expect(consentBox()).not.toBeChecked();
    expect(screen.getAllByText("(required)")).toHaveLength(2); // the two names; the agreement is required by its own sentence
  });

  it("shows the agreement in words a worker can read before they tick it", () => {
    render(<Page />);
    expect(screen.getByText("Clients who post a job in my trade can see my name and phone number.")).toBeVisible();
    expect(screen.getByText("You can turn this off later on your profile.")).toBeVisible();
  });

  it("refuses to submit without a name or the agreement, and says what is missing", async () => {
    render(<Page />);
    await submitWorker();
    expect(await screen.findByText("Enter your first name.")).toBeVisible();
    expect(screen.getByText("Enter your last name.")).toBeVisible();
    expect(screen.getByText(/Agree to continue/)).toBeVisible();
    expect(createAccount).not.toHaveBeenCalled();
  });

  it("refuses a name that is only spaces", async () => {
    render(<Page />);
    await userEvent.type(firstName(), "   ");
    await userEvent.type(lastName(), "Wanjiru");
    await userEvent.click(consentBox());
    await submitWorker();
    expect(await screen.findByText("Enter your first name.")).toBeVisible();
    expect(createAccount).not.toHaveBeenCalled();
  });

  it("refuses digits and symbols in a name", async () => {
    render(<Page />);
    await fillWorkerDetails("Amina2", "Wanjiru");
    await submitWorker();
    expect(await screen.findByText("Use letters, spaces, hyphens and apostrophes only.")).toBeVisible();
    expect(createAccount).not.toHaveBeenCalled();
  });

  it("stops a name at 60 characters", () => {
    render(<Page />);
    expect(firstName()).toHaveAttribute("maxlength", "60");
    expect(lastName()).toHaveAttribute("maxlength", "60");
  });

  it("accepts a hyphenated name, an apostrophe and accents, and sends them trimmed", async () => {
    createAccount.mockResolvedValue({ account: { account_id: "a-1", phone: "712345678", role: "worker" }, worker_profile_id: null, postings: 0 });
    render(<Page />);
    await fillWorkerDetails("  Mary-Anne ", "O'Neil  Zoë");
    await submitWorker();
    expect(createAccount).toHaveBeenCalledWith(
      expect.objectContaining({ first_name: "Mary-Anne", last_name: "O'Neil Zoë", contact_consent: true }),
    );
  });

  it("shows the server's complaint on the field it names", async () => {
    const { ApiError } = await import("@/lib/api");
    createAccount.mockRejectedValue(new ApiError(400, "invalid_request", "first_name is required", "first_name"));
    render(<Page />);
    await fillWorkerDetails();
    await submitWorker();
    expect(await screen.findByText("first_name is required")).toBeVisible();
  });

  it("clears the name and the agreement from the page once the account is made", async () => {
    createAccount.mockResolvedValue({ account: { account_id: "a-1", phone: "712345678", role: "worker" }, worker_profile_id: null, postings: 0 });
    render(<Page />);
    await fillWorkerDetails();
    await submitWorker();
    await waitFor(() => expect(createAccount).toHaveBeenCalled());
    await waitFor(() => expect(firstName()).toHaveValue(""));
    expect(lastName()).toHaveValue("");
    expect(consentBox()).not.toBeChecked();
  });
});

describe("a client signing up", () => {
  it("is not asked for a name or an agreement", async () => {
    render(<Page />);
    await userEvent.click(screen.getByRole("radio", { name: "I'm a client" }));
    expect(screen.queryByLabelText(/^First name/)).toBeNull();
    expect(screen.queryByLabelText(/^Last name/)).toBeNull();
    expect(screen.queryByRole("checkbox")).toBeNull();
  });

  it("sends only the number, the PIN and the role, even after typing a worker's name first", async () => {
    createAccount.mockResolvedValue({ account: { account_id: "a-1", phone: "712345678", role: "client" }, worker_profile_id: null, postings: 0 });
    render(<Page />);
    await fillWorkerDetails();
    await userEvent.click(screen.getByRole("radio", { name: "I'm a client" }));
    await submitWorker();
    expect(createAccount).toHaveBeenCalledWith({ phone: "712345678", pin: "4821", role: "client" });
  });
});

describe("the PIN and its confirmation", () => {
  it("are two separate fields; the second is never filled in from the first", async () => {
    render(<Page />);
    await typePin("Create a 4-digit PIN", "4821");

    for (const box of screen.getAllByLabelText(/^Confirm PIN, digit/)) {
      expect(box).toHaveValue("");
    }
  });

  it("says so as soon as the two differ, without waiting for submit", async () => {
    render(<Page />);
    await typePin("Create a 4-digit PIN", "4821");
    await typePin("Confirm PIN", "4822");

    expect(await screen.findByText("The two PINs are different.")).toBeVisible();
  });

  it("says nothing once they match", async () => {
    render(<Page />);
    await typePin("Create a 4-digit PIN", "4821");
    await typePin("Confirm PIN", "4821");

    expect(screen.queryByText("The two PINs are different.")).toBeNull();
  });

  it("can be revealed so the person can check what they typed", async () => {
    render(<Page />);
    await typePin("Create a 4-digit PIN", "4821");

    const [show] = screen.getAllByRole("button", { name: "Show" });
    expect(screen.getAllByLabelText(/^Create a 4-digit PIN, digit/)[0]).toHaveAttribute("type", "password");
    await userEvent.click(show);
    expect(screen.getAllByLabelText(/^Create a 4-digit PIN, digit/)[0]).toHaveAttribute("type", "text");
  });
});
