/**
 * The landing page says what the system does, with one worked example, and offers the two
 * ways in. It claims nothing it cannot show: no figures, no images.
 */

import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/page";

const engine = { ready: true, candidateJobs: 280, unreachable: false, recheck: vi.fn() };
const redirect = vi.fn();

vi.mock("next/font/google", () => ({ Nunito_Sans: () => ({ variable: "heading" }) }));
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
  it("has one heading and one sentence saying what the system does", () => {
    render(<Page />);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByText(/understands how tradespeople describe their work/)).toBeInTheDocument();
  });

  it("shows the path from what a worker writes to the trade to the jobs", () => {
    render(<Page />);
    const path = screen.getByRole("list", { name: "An example" });
    const steps = within(path).getAllByRole("listitem");
    expect(steps).toHaveLength(3);
    expect(steps[0]).toHaveTextContent("fundi wa umeme");
    expect(steps[1]).toHaveTextContent("Electrician");
    expect(steps[2]).toHaveTextContent("Jobs that need those skills");
  });

  it("leads to create-account with the right role from each entry point", () => {
    render(<Page />);
    expect(screen.getByRole("link", { name: "I'm looking for work" })).toHaveAttribute(
      "href",
      "/create-account?role=worker",
    );
    expect(screen.getByRole("link", { name: "I need a fundi" })).toHaveAttribute(
      "href",
      "/create-account?role=client",
    );
  });

  it("keeps a way back to sign-in for returning users", () => {
    render(<Page />);
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/sign-in");
  });

  it("describes how it works in three steps", () => {
    render(<Page />);
    const row = within(screen.getByRole("region", { name: "How it works" })).getAllByRole("listitem");
    expect(row.map((item) => item.textContent?.replace(/^\d/, ""))).toEqual([
      "Describe your work in your own words",
      "We work out your trade",
      "See matching jobs with the reasons for each",
    ]);
  });

  it("says it is a student project and not a live service", () => {
    render(<Page />);
    expect(screen.getByRole("contentinfo")).toHaveTextContent(
      "final-year project at Strathmore University. It is not a live service.",
    );
  });

  it("has no images and no figures", () => {
    const { container } = render(<Page />);
    expect(container.querySelector("img, picture, video")).toBeNull();
    expect(container.textContent).not.toMatch(/\d+\s*(%|workers|jobs|users)/);
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
});
