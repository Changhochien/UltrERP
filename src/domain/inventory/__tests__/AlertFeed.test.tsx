import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { AlertFeed } from "../components/AlertFeed";

vi.mock("../components/AlertPanel", () => ({
  AlertPanel: () => <div>alert-panel</div>,
}));

afterEach(() => {
  cleanup();
});

describe("AlertFeed", () => {
  it("renders the live inventory alert panel surface", () => {
    render(<AlertFeed />);

    expect(screen.getByText("alert-panel")).toBeTruthy();
  });
});