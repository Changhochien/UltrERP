import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { CommandBar } from "../components/CommandBar";

describe("CommandBar", () => {
  it("uses shared UI primitives for search and action affordances", () => {
    const onAdjustStock = vi.fn();
    const onNewTransfer = vi.fn();
    const onNewOrder = vi.fn();
    const onSearch = vi.fn();

    render(
      <CommandBar
        searchValue="bolt"
        onAdjustStock={onAdjustStock}
        onNewTransfer={onNewTransfer}
        onNewOrder={onNewOrder}
        onSearch={onSearch}
      />,
    );

    const region = screen.getByRole("region", { name: "Inventory commands" });

    expect(region.className).toContain("rounded-2xl");
    expect(region.className).not.toContain("command-bar");

    fireEvent.change(screen.getByRole("searchbox", { name: "Search products" }), {
      target: { value: "gear" },
    });

    expect(onSearch).toHaveBeenCalledWith("gear");

    fireEvent.click(screen.getByRole("button", { name: /Adjust Stock/i }));
    fireEvent.click(screen.getByRole("button", { name: /New Transfer/i }));
    fireEvent.click(screen.getByRole("button", { name: /New Order/i }));

    expect(onAdjustStock).toHaveBeenCalledTimes(1);
    expect(onNewTransfer).toHaveBeenCalledTimes(1);
    expect(onNewOrder).toHaveBeenCalledTimes(1);
  });
});