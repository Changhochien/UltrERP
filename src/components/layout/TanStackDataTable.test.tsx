import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { TanStackDataTable } from "./TanStackDataTable";

if (typeof PointerEvent === "undefined") {
  class TestPointerEvent extends MouseEvent {}
  vi.stubGlobal("PointerEvent", TestPointerEvent);
}

afterEach(() => {
  cleanup();
});

describe("TanStackDataTable", () => {
  it("cycles sorting through ascending, descending, and off states", () => {
    const data = [
      { id: "row-1", name: "Bravo" },
      { id: "row-2", name: "Alpha" },
    ];

    render(
      <TanStackDataTable
        columns={[
          {
            id: "name",
            header: "Name",
            sortable: true,
            getSortValue: (row) => row.name,
            cell: (row) => <span data-testid="name-cell">{row.name}</span>,
          },
        ]}
        data={data}
      />,
    );

    const headerButton = screen.getByRole("button", { name: "Name" });
    const headerCell = screen.getByText("Name").closest("th");

    expect(screen.getAllByTestId("name-cell").map((cell) => cell.textContent)).toEqual(["Bravo", "Alpha"]);
    expect(headerCell?.getAttribute("aria-sort")).toBeNull();

    fireEvent.click(headerButton);

    expect(screen.getAllByTestId("name-cell").map((cell) => cell.textContent)).toEqual(["Alpha", "Bravo"]);
    expect(headerCell?.getAttribute("aria-sort")).toBe("ascending");

    fireEvent.click(headerButton);

    expect(screen.getAllByTestId("name-cell").map((cell) => cell.textContent)).toEqual(["Bravo", "Alpha"]);
    expect(headerCell?.getAttribute("aria-sort")).toBe("descending");

    fireEvent.click(headerButton);

    expect(screen.getAllByTestId("name-cell").map((cell) => cell.textContent)).toEqual(["Bravo", "Alpha"]);
    expect(headerCell?.getAttribute("aria-sort")).toBeNull();
  });

  it("fires the pagination callback when the page changes", () => {
    const onPageChange = vi.fn();

    render(
      <TanStackDataTable
        columns={[
          {
            id: "name",
            header: "Name",
            cell: (row) => row.name,
          },
        ]}
        data={[{ id: "row-1", name: "Alpha" }]}
        page={1}
        pageSize={1}
        totalItems={3}
        onPageChange={onPageChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Go to next page/i }));

    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("renders sticky-header styling and resize hooks when enabled", () => {
    render(
      <TanStackDataTable
        columns={[
          {
            id: "name",
            header: "Name",
            cell: (row) => row.name,
            size: 160,
          },
        ]}
        data={[{ id: "row-1", name: "Alpha" }]}
        stickyHeader
        enableColumnResizing
      />,
    );

    const resizeHandle = screen.getByLabelText("Resize Name");
    const headerCell = screen.getAllByRole("columnheader")[0];

    expect(headerCell.style.position).toBe("sticky");
    expect(headerCell.style.top).toBe("0px");
    expect(resizeHandle).toBeTruthy();

    fireEvent.mouseDown(resizeHandle, { clientX: 160 });
    fireEvent.mouseMove(document, { clientX: 220 });
    fireEvent.mouseUp(document);

    const resizedWidth = Number.parseFloat(headerCell?.style.width ?? "0");

    expect(resizedWidth).not.toBe(180);
    expect(resizedWidth).toBeGreaterThanOrEqual(120);
  });

  it("shows a bulk-action bar when rows are selected", () => {
    render(
      <TanStackDataTable
        columns={[
          {
            id: "name",
            header: "Name",
            cell: (row) => row.name,
          },
        ]}
        data={[
          { id: "row-1", name: "Alpha" },
          { id: "row-2", name: "Bravo" },
        ]}
        getRowId={(row) => row.id}
        rowLabel={(row) => `${row.name} row`}
        enableRowSelection
        renderBulkActions={({ selectedRows }) => (
          <button type="button">Archive {selectedRows.length}</button>
        )}
      />,
    );

    fireEvent.click(screen.getByLabelText("Select Alpha row"));

    expect(screen.getByText("1 selected")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Archive 1" })).toBeTruthy();
  });

  it("preserves row labels, row classes, and row activation", () => {
    const onRowClick = vi.fn();

    render(
      <TanStackDataTable
        columns={[
          {
            id: "name",
            header: "Name",
            cell: (row) => row.name,
          },
        ]}
        data={[{ id: "row-1", name: "Alpha", warning: true }]}
        getRowId={(row) => row.id}
        rowLabel={(row) => `${row.name} row`}
        getRowClassName={(row) => (row.warning ? "bg-warning/10" : undefined)}
        onRowClick={onRowClick}
      />,
    );

    const row = screen.getByRole("button", { name: "Alpha row" });
    expect(row.className.includes("bg-warning/10")).toBe(true);

    fireEvent.click(row);

    expect(onRowClick).toHaveBeenCalledWith({ id: "row-1", name: "Alpha", warning: true });
  });
});