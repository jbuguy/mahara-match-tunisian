import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GovernorateMap } from "./GovernorateMap";
import { metricColorClass } from "./governorateMapUtils";

describe("GovernorateMap", () => {
  it("maps fixed metric breakpoints to five colour classes", () => {
    expect(metricColorClass("candidates", 0)).toBe(1);
    expect(metricColorClass("candidates", 25)).toBe(3);
    expect(metricColorClass("candidates", 100)).toBe(5);
  });

  it("renders the accessible controls snapshot", () => {
    const { container } = render(<GovernorateMap onSelect={vi.fn()} data={[]} />);
    expect(screen.getByRole("button", { name: "Afficher en tableau" })).toBeTruthy();
    expect(container).toMatchSnapshot();
  });
});
