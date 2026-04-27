import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CustomerSearchBar } from "@/domain/customers/components/CustomerSearchBar";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("CustomerSearchBar", () => {
  it("does not call onSearch after unmount", () => {
    vi.useFakeTimers();
    const onSearch = vi.fn();

    const view = render(<CustomerSearchBar onSearch={onSearch} debounceMs={300} />);

    fireEvent.change(screen.getByLabelText("Search customers"), {
      target: { value: "Acme" },
    });

    view.unmount();
    vi.advanceTimersByTime(300);

    expect(onSearch).not.toHaveBeenCalled();
  });
});