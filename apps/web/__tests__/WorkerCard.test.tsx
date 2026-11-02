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
});
