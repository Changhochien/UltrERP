import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import i18n from "i18next";
import { format } from "date-fns";
import type { DateRange } from "react-day-picker";
import * as React from "react";

import { DatePicker } from "../../components/ui/DatePicker";
import { DateRangePicker } from "../../components/ui/DateRangePicker";

function formatDate(value: Date | undefined) {
  return value ? format(value, "yyyy-MM-dd") : undefined;
}

function formatRange(value: DateRange | undefined) {
  return value
    ? {
        from: formatDate(value.from),
        to: formatDate(value.to),
      }
    : undefined;
}

async function clickCalendarDay(labelFragment: string) {
  const fallbackDay = labelFragment.match(/(\d{1,2})(?!.*\d)/)?.[1];
  const dialog = await screen.findByRole("dialog");
  let dayButton: HTMLElement | undefined;

  await waitFor(() => {
    dayButton = within(dialog).getAllByRole("button").find((button) =>
      button.getAttribute("aria-label")?.includes(labelFragment) ||
      (fallbackDay !== undefined && button.textContent?.trim() === fallbackDay),
    );

    if (!dayButton) {
      throw new Error(`Could not find calendar day button containing "${labelFragment}".`);
    }
  });

  if (!dayButton) {
    throw new Error(`Could not find calendar day button containing "${labelFragment}".`);
  }

  fireEvent.click(dayButton);
}

function ControlledDateRangePicker() {
  const [value, setValue] = React.useState<DateRange | undefined>(undefined);

  return (
    <DateRangePicker
      id="report-date-range"
      aria-label="Report date range"
      value={value}
      onChange={setValue}
      placeholder="Select a date range"
      defaultMonth={new Date(2026, 3, 1)}
    />
  );
}

describe("DatePicker", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  afterEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("opens the calendar popover and selects a single day", async () => {
    const onChange = vi.fn();

    render(
      <DatePicker
        id="invoice-date"
        aria-label="Invoice date"
        value={undefined}
        onChange={onChange}
        placeholder="Select a date"
        defaultMonth={new Date(2026, 3, 1)}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Invoice date" }));

    expect(screen.getByText("April 2026")).toBeTruthy();

    await clickCalendarDay("April 15");

    expect(formatDate(onChange.mock.calls[0]?.[0])).toBe("2026-04-15");
  });

  it("formats the selected value using the active locale", async () => {
    await i18n.changeLanguage("zh-Hant");

    render(
      <DatePicker
        id="statement-date"
        aria-label="Statement date"
        value={new Date(2026, 3, 15)}
        onChange={() => undefined}
      />,
    );

    expect(screen.getByRole("button", { name: "Statement date" }).textContent).toContain(
      "2026年4月15日",
    );
  });
});

describe("DateRangePicker", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("selects a start and end date for a range", async () => {
    render(<ControlledDateRangePicker />);

    fireEvent.click(screen.getByRole("button", { name: "Report date range" }));

    await clickCalendarDay("April 10");
    await clickCalendarDay("April 18");

    expect(screen.getByRole("button", { name: "Report date range" }).textContent).toContain(
      "Apr 10, 2026 - Apr 18, 2026",
    );

    expect(formatRange({ from: new Date(2026, 3, 10), to: new Date(2026, 3, 18) })).toEqual({
      from: "2026-04-10",
      to: "2026-04-18",
    });
  });

  it("allows a same-day range", async () => {
    render(<ControlledDateRangePicker />);

    fireEvent.click(screen.getByRole("button", { name: "Report date range" }));

    await clickCalendarDay("April 10");

    expect(screen.getByRole("button", { name: "Report date range" }).textContent).toContain(
      "Apr 10, 2026 - Apr 10, 2026",
    );
  });
});