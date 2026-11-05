/**
 * The landing page says what the system does, which trades it understands and how it works, and offers the
 * ways in. It claims nothing the system cannot back, shows no worker, and has no search.
 */

import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/page";

const engine = { ready: true, candidateJobs: 280, unreachable: false, recheck: vi.fn() };
const redirect = vi.fn();

vi.mock("@/components/EngineStatus", () => ({ useEngineStatus: () => engine }));
vi.mock("@/components/SessionProvider", () => ({
  useRedirectIfSignedIn: () => redirect(),
  useSession: () => ({ session: null, loading: false }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  engine.ready = true;
  engine.unreachable = false;
});

describe("the landing page", () => {
  it("has one heading, and says in one sentence what the system does", () => {
    render(<Page />);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Work that fits your hands.");
    expect(screen.getByText(/understands how tradespeople describe their work/)).toBeInTheDocument();
  });

  it("leads to create-account with the right role from each hero button", () => {
    render(<Page />);
    expect(screen.getByRole("link", { name: /I'm looking for work/ })).toHaveAttribute("href", "/create-account?role=worker");
    expect(screen.getByRole("link", { name: /I need a fundi/ })).toHaveAttribute("href", "/create-account?role=client");
  });

  it("repeats the two ways in further down, to the same places", () => {
    render(<Page />);
    expect(screen.getByRole("link", { name: "Create a worker account" })).toHaveAttribute("href", "/create-account?role=worker");
    expect(screen.getByRole("link", { name: "Create a client account" })).toHaveAttribute("href", "/create-account?role=client");
  });

  it("has a way to sign in at the top and at the foot, both to /sign-in", () => {
    render(<Page />);
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/sign-in");
    expect(screen.getByRole("link", { name: "Sign in to your account" })).toHaveAttribute("href", "/sign-in");
  });

  it("scrolls to the two entry cards from Get started, and to the steps from How it works", () => {
    render(<Page />);
    expect(screen.getByRole("link", { name: "Get started" })).toHaveAttribute("href", "#start");
    expect(screen.getByRole("link", { name: "How it works" })).toHaveAttribute("href", "#how-it-works");
    expect(document.getElementById("start")).not.toBeNull();
    expect(document.getElementById("how-it-works")).not.toBeNull();
  });
});

describe("the trades", () => {
  it("lists the eleven trades the system understands, each with the term it knows", () => {
    render(<Page />);
    const trades = within(screen.getByRole("list", { name: /Trades and the terms we know/ })).getAllByRole("listitem");
    expect(trades).toHaveLength(11);
    expect(trades[0]).toHaveTextContent("fundi wa umeme");
    expect(trades[0]).toHaveTextContent("electrician");
    expect(trades.map((t) => t.textContent).join(" ")).toMatch(/fundi bomba.*plumber/);
  });

  it("offers nothing to click or search: the list is text", () => {
    render(<Page />);
    const list = screen.getByRole("list", { name: /Trades and the terms we know/ });
    expect(within(list).queryAllByRole("link")).toHaveLength(0);
    expect(within(list).queryAllByRole("button")).toHaveLength(0);
    expect(screen.queryByRole("searchbox")).toBeNull();
    expect(screen.queryByRole("textbox")).toBeNull();
  });
});

describe("how it works", () => {
  it("has three steps", () => {
    render(<Page />);
    const steps = within(screen.getByRole("region", { name: /How KaziForce works/ })).getAllByRole("heading", { level: 3 });
    expect(steps.map((h) => h.textContent)).toEqual(["Say what you do", "We work out your trade", "See jobs, and why"]);
  });

  it("labels its worker example as an example, so it cannot read as a testimonial", () => {
    render(<Page />);
    expect(screen.getAllByText("Example").length).toBeGreaterThanOrEqual(2);
  });
});

describe("what the page does not claim", () => {
  const text = () => render(<Page />).container.textContent ?? "";

  it("has no counts, rates or percentages", () => {
    expect(text()).not.toMatch(/\d+\s*\+|\bKES\b|\d+\s*%|typical|over \d|\d{2,} (workers|fundis|wiremen|jobs|users)/i);
  });

  it("has no verified, trusted or free promises", () => {
    expect(text()).not.toMatch(/verified|trust|\bfree\b|commission|middlem|guarantee|best|top-rated|quality/i);
  });

  it("names no feature the system lacks", () => {
    expect(text()).not.toMatch(/\bSMS\b|one-time|WhatsApp|quote|estimate|search|speak|project rate|password/i);
  });

  it("does not rank anything", () => {
    expect(text()).not.toMatch(/score|ranked|best fit|top match|recommended|leaderboard/i);
  });

  it("shows no worker's name, number or profile", () => {
    const { container } = render(<Page />);
    expect(container.textContent).not.toMatch(/Amina|Joseph|Grace|Wanjiru|Otieno|Achieng/);
    expect(container.textContent).not.toMatch(/\+?254|\b07\d|\b7\d{2} ?\d{3} ?\d{3}/);
    expect(container.querySelector('a[href^="tel:"], a[href*="/client/workers"]')).toBeNull();
  });

  it("has no images and loads no icon font: its icons are inline and hidden from assistive technology", () => {
    const { container } = render(<Page />);
    expect(container.querySelector("img, picture, video")).toBeNull();
    for (const svg of container.querySelectorAll("svg")) expect(svg).toHaveAttribute("aria-hidden", "true");
  });

  it("says the workers a client sees are a sample, not a ranking", () => {
    render(<Page />);
    expect(screen.getByText(/a sample of the trade, not a ranking/)).toBeInTheDocument();
  });
});

describe("the page's behaviour", () => {
  it("has a footer with the name and the year, and nothing else", () => {
    render(<Page />);
    expect(screen.getByRole("contentinfo")).toHaveTextContent(/^KaziForce © 2026$/);
  });

  it("sends a signed-in visitor on to their own home", () => {
    render(<Page />);
    expect(redirect).toHaveBeenCalled();
  });

  it("shows the startup notice while the matching service is still loading", () => {
    engine.ready = false;
    render(<Page />);
    expect(screen.getByRole("status")).toHaveTextContent("Preparing the matching service");
  });

  it("shows no notice once the service is ready", () => {
    render(<Page />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("puts the startup notice after the top bar and before the content", () => {
    engine.ready = false;
    const { container } = render(<Page />);
    const order = [container.querySelector("header"), screen.getByRole("status"), container.querySelector("main")];
    for (let i = 0; i < order.length - 1; i++) {
      expect(order[i]!.compareDocumentPosition(order[i + 1]!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });
});
