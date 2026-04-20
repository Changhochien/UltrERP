import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { Breadcrumb } from "../../components/ui/Breadcrumb";

describe("Breadcrumb", () => {
  it("renders clickable ancestors and a non-clickable current crumb", () => {
    render(
      <MemoryRouter>
        <Breadcrumb
          items={[
            { label: "Customers", href: "/customers" },
            { label: "Acme Corp" },
          ]}
        />
      </MemoryRouter>,
    );

    expect(screen.getByRole("navigation", { name: "Breadcrumb" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Customers" })).toBeTruthy();
    expect(screen.getByText("Acme Corp").getAttribute("aria-current")).toBe("page");
  });

  it("renders a single current crumb for list pages", () => {
    render(
      <MemoryRouter>
        <Breadcrumb items={[{ label: "Orders" }]} />
      </MemoryRouter>,
    );

    expect(screen.queryByRole("link", { name: "Orders" })).toBeNull();
    expect(screen.getByText("Orders").getAttribute("aria-current")).toBe("page");
  });

  it("includes a collapsed mobile trail with an ellipsis for deeper paths", () => {
    render(
      <MemoryRouter>
        <Breadcrumb
          items={[
            { label: "Inventory", href: "/inventory" },
            { label: "Suppliers", href: "/inventory/suppliers" },
            { label: "Acme Supply", href: "/inventory/suppliers/supplier-1" },
            { label: "Contacts" },
          ]}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText("…")).toBeTruthy();
    expect(screen.getAllByText("Contacts").length).toBeGreaterThan(0);
  });
});