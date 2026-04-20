import "../helpers/i18n";

import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { useToast } from "../../hooks/useToast";
import { ToastProvider } from "../../providers/ToastProvider";

function ToastHarness() {
  const { dismiss, error, success } = useToast();

  return (
    <div>
      <button type="button" onClick={() => success("Saved", "Order confirmation completed.")}>Show success</button>
      <button type="button" onClick={() => error("Failed", "Server rejected the mutation.")}>Show error</button>
      <button
        type="button"
        onClick={() => {
          for (let index = 1; index <= 6; index += 1) {
            success(`Toast ${index}`);
          }
        }}
      >
        Show many
      </button>
      <button type="button" onClick={() => dismiss()}>Dismiss all</button>
    </div>
  );
}

describe("ToastProvider", () => {
  it("renders and dismisses a toast through the provider", async () => {
    render(
      <ToastProvider>
        <ToastHarness />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Show success" }));

    expect(await screen.findByText("Saved")).toBeTruthy();
    expect(screen.getByText("Order confirmation completed.")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Dismiss notification" }));

    await waitFor(() => {
      expect(screen.queryByText("Saved")).toBeNull();
    }, { timeout: 1200 });
  });

  it("keeps only the newest five toasts when mutations stack", async () => {
    render(
      <ToastProvider>
        <ToastHarness />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Show many" }));

    expect(await screen.findByText("Toast 6")).toBeTruthy();
    expect(screen.queryByText("Toast 1")).toBeNull();
    expect(screen.getAllByRole("status").length).toBe(5);
  });
});