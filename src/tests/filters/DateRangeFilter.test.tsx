import * as React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DateRangeFilter } from "../../components/filters/DateRangeFilter";

function ControlledDateRangeFilter() {
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");

  return (
    <DateRangeFilter
      dateFrom={dateFrom}
      dateTo={dateTo}
      onDateFromChange={setDateFrom}
      onDateToChange={setDateTo}
    />
  );
}

describe("DateRangeFilter", () => {
  it("renders independent bound pickers instead of native date inputs and supports an upper bound only", () => {
    const { container } = render(<ControlledDateRangeFilter />);

    expect(container.querySelector('input[type="date"]')).toBeNull();
    expect(screen.getByRole("button", { name: "From date" }).textContent).toContain(
      "From",
    );
    expect(screen.getByRole("button", { name: "To date" }).textContent).toContain("To");

    fireEvent.click(screen.getByRole("button", { name: "To date" }));

    const dayButton = screen.getAllByRole("button").find((button) =>
      button.getAttribute("aria-label")?.includes("April 18"),
    );

    if (!dayButton) {
      throw new Error('Could not find calendar day button containing "April 18".');
    }

    fireEvent.click(dayButton);

    expect(screen.getByRole("button", { name: "From date" }).textContent).toContain("From");
    expect(screen.getByRole("button", { name: "To date" }).textContent).toContain(
      "Apr 18, 2026",
    );
  });
});