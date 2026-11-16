/**
 * A worker on the client's confirmation screen: their own words first, the trade as a tag,
 * the practical facts after. Nothing that reads as a score or a rank.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WorkerCard } from "@/components/WorkerCard";
import type { TradeWorker } from "@/lib/types";

const worker: TradeWorker = {
  describes_as: "fundi wa umeme, wiring, solar installation",
  location: "Nairobi - Kasarani",
  availability: "Full-time",
  rate_expectation: 2500,
};

describe("WorkerCard", () => {
  it("shows the worker's own description, as they wrote it", () => {
    render(<WorkerCard worker={worker} trade="electrician" />);
    expect(screen.getByText("“fundi wa umeme, wiring, solar installation”")).toBeInTheDocument();
  });

  it("shows the trade as a tag", () => {
    render(<WorkerCard worker={worker} trade="electrician" />);
    expect(screen.getByText("electrician")).toBeInTheDocument();
  });

  it("shows location, availability and the daily rate", () => {
    render(<WorkerCard worker={worker} trade="electrician" />);
    expect(screen.getByText("Nairobi - Kasarani")).toBeInTheDocument();
    expect(screen.getByText("Full-time")).toBeInTheDocument();
    expect(screen.getByText(/2,500/)).toBeInTheDocument();
  });

  it("says what is not stated instead of leaving a gap", () => {
    render(
      <WorkerCard
        worker={{ ...worker, location: null, availability: null, rate_expectation: null }}
        trade="electrician"
      />,
    );
    expect(screen.getByText("Location not stated")).toBeInTheDocument();
    expect(screen.getByText("Availability not stated")).toBeInTheDocument();
    expect(screen.getByText("Rate not stated")).toBeInTheDocument();
  });

  it("carries no score, rank or number that implies an order", () => {
    const { container } = render(<WorkerCard worker={worker} trade="electrician" />);
    expect(container.textContent).not.toMatch(/score|rank|match|best|top|#\d/i);
  });

  it("is anonymous, with no link, when the worker has no name to show", () => {
    render(<WorkerCard worker={worker} trade="electrician" postingId="p-1" />);
    expect(screen.queryByRole("link")).toBeNull();
  });
});

describe("WorkerCard for a worker who has agreed to be shown", () => {
  const named: TradeWorker = { ...worker, public_id: "11111111-2222-4333-8444-555555555555", name: "Amina Wanjiru" };

  it("shows the name as a link to their profile", () => {
    render(<WorkerCard worker={named} trade="electrician" />);
    expect(screen.getByRole("link", { name: "Amina Wanjiru" })).toHaveAttribute(
      "href",
      "/client/workers/11111111-2222-4333-8444-555555555555",
    );
  });

  it("carries the posting along so the profile can link back to it", () => {
    render(<WorkerCard worker={named} trade="electrician" postingId="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee" />);
    expect(screen.getByRole("link", { name: "Amina Wanjiru" })).toHaveAttribute(
      "href",
      "/client/workers/11111111-2222-4333-8444-555555555555?posting=aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
    );
  });

  it("still shows their own words, the trade and the facts, and no phone number", () => {
    const { container } = render(<WorkerCard worker={named} trade="electrician" />);
    expect(screen.getByText("“fundi wa umeme, wiring, solar installation”")).toBeInTheDocument();
    expect(screen.getByText("electrician")).toBeInTheDocument();
    expect(screen.getByText("Nairobi - Kasarani")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/\+?254|tel:|\b07\d/);
  });

  it("still carries no score, rank or number that implies an order", () => {
    const { container } = render(<WorkerCard worker={named} trade="electrician" />);
    expect(container.textContent).not.toMatch(/score|rank|match|best|top|#\d/i);
  });

  it("is still one article, drawn no larger than an anonymous card; the only difference is that it can be opened", () => {
    const { container: plain } = render(<WorkerCard worker={worker} trade="electrician" />);
    const { container: withName } = render(<WorkerCard worker={named} trade="electrician" />);
    expect(plain.querySelectorAll("article")).toHaveLength(1);
    expect(withName.querySelectorAll("article")).toHaveLength(1);
    // Both share the base card style, so neither is larger or earlier; the named one adds only the openable style.
    const named_ = withName.querySelector("article")!.className.split(" ").filter(Boolean);
    const plain_ = plain.querySelector("article")!.className.split(" ").filter(Boolean);
    expect(plain_).toHaveLength(1);
    expect(named_.slice(0, 1)).toEqual(plain_);
    expect(named_).toHaveLength(2);
  });

  it("looks openable: a link on the name, and a visible \"Open profile\" cue that is not read twice", () => {
    const { container } = render(<WorkerCard worker={named} trade="electrician" />);
    expect(screen.getByRole("link", { name: named.name! })).toHaveAttribute("href", expect.stringContaining("/client/workers/"));
    const cue = container.querySelector('[aria-hidden="true"]');
    expect(cue).toHaveTextContent("Open profile");
  });

  it("gives a card that cannot be opened no link and no cue", () => {
    const { container } = render(<WorkerCard worker={worker} trade="electrician" />);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(container.textContent).not.toMatch(/Open profile/);
  });
});
