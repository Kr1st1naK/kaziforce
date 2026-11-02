/**
 * Account creation: the number the numbering plan allows, and a confirmation PIN
 * that is typed rather than filled in for the person.
 *
 * Prefilling the second PIN would confirm a typo against itself, so the screen
 * keeps both fields and says as soon as they differ.
 */

import { render, screen } from "@testing-library/react";
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
    await userEvent.type(phoneField(), "712345678");
    await typePin("Create a 4-digit PIN", "4821");
    await typePin("Confirm PIN", "4821");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(createAccount).toHaveBeenCalledWith({ phone: "712345678", pin: "4821", role: "worker" });
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
