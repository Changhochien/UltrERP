import "../helpers/i18n";

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  QuickEntryDialog,
} from "../../components/ui/QuickEntryDialog";
import { Spinner } from "../../components/ui/Spinner";
import {
  StatusBadge,
  resolveStatusBadgeVariant,
} from "../../components/ui/StatusBadge";

describe("shared Story 22.6 UI primitives", () => {
  it("renders an accessible spinner label when requested", () => {
    render(<Spinner size="lg" label="Loading customers" />);

    const spinner = screen.getByRole("status", { name: "Loading customers" });
    expect(spinner.className).toContain("size-5");
    expect(spinner.className).toContain("animate-spin");
  });

  it("maps known statuses through the shared resolver", () => {
    expect(resolveStatusBadgeVariant("paid")).toBe("success");
    expect(resolveStatusBadgeVariant("partially_received")).toBe("warning");
    expect(resolveStatusBadgeVariant("open", { overrides: { open: "warning" } })).toBe("warning");
    expect(resolveStatusBadgeVariant("CUSTOM", { overrides: { custom: "info" } })).toBe("info");
    expect(resolveStatusBadgeVariant(undefined, { defaultVariant: "warning" })).toBe("warning");

    render(<StatusBadge status="dead_letter" />);

    const badge = screen.getByText("Dead Letter");
    expect(badge.className).toContain("tone-destructive");
  });

  it("renders a controlled quick-entry dialog with busy state and close handling", () => {
    const onOpenChange = vi.fn();

    render(
      <QuickEntryDialog
        open
        onOpenChange={onOpenChange}
        title="Create new customer"
        description="Create and select the customer without leaving the form."
        busy
      >
        <div>Dialog body</div>
      </QuickEntryDialog>,
    );

    const dialog = screen.getByRole("dialog", { name: "Create new customer" });
    expect(dialog.getAttribute("aria-busy")).toBe("true");
    expect(screen.getByText("Dialog body")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onOpenChange).toHaveBeenCalled();
    expect(onOpenChange.mock.calls[0]?.[0]).toBe(false);
  });
});