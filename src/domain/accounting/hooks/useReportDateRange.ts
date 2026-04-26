/**
 * Hook for common report date range selection (Epic 26.3).
 */

import { useState, useCallback, useMemo } from "react";

export interface DateRange {
  from: Date;
  to: Date;
}

export interface DateRangePresets {
  [key: string]: DateRange | undefined;
}

function getMonthRange(monthOffset: number): DateRange {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();

  const from = new Date(year, month + monthOffset, 1);
  const to = new Date(year, month + monthOffset + 1, 0);

  return { from, to };
}

function getQuarterRange(quarterOffset: number): DateRange {
  const now = new Date();
  const year = now.getFullYear();
  const currentQuarter = Math.floor(now.getMonth() / 3);
  const quarter = currentQuarter + quarterOffset;

  let targetYear = year;
  let targetQuarter = quarter;

  if (targetQuarter < 0) {
    targetYear -= 1;
    targetQuarter += 4;
  } else if (targetQuarter > 3) {
    targetYear += 1;
    targetQuarter -= 4;
  }

  const from = new Date(targetYear, targetQuarter * 3, 1);
  const to = new Date(targetYear, targetQuarter * 3 + 3, 0);

  return { from, to };
}

function getYearRange(yearOffset: number): DateRange {
  const now = new Date();
  const year = now.getFullYear() + yearOffset;

  return {
    from: new Date(year, 0, 1),
    to: new Date(year, 11, 31),
  };
}

export function useReportDateRange() {
  const now = new Date();
  const currentMonthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const currentMonthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0);

  const [fromDate, setFromDate] = useState<Date | null>(currentMonthStart);
  const [toDate, setToDate] = useState<Date | null>(currentMonthEnd);
  const [selectedPreset, setSelectedPreset] = useState<string>("this_month");

  const presets: DateRangePresets = useMemo(
    () => ({
      this_month: getMonthRange(0),
      last_month: getMonthRange(-1),
      this_quarter: getQuarterRange(0),
      last_quarter: getQuarterRange(-1),
      this_year: getYearRange(0),
      last_year: getYearRange(-1),
    }),
    []
  );

  const handleFromDateChange = useCallback(
    (date: Date | null | undefined) => {
      setFromDate(date ?? null);
      setSelectedPreset("custom");
    },
    []
  );

  const handleToDateChange = useCallback(
    (date: Date | null | undefined) => {
      setToDate(date ?? null);
      setSelectedPreset("custom");
    },
    []
  );

  return {
    fromDate,
    toDate,
    setFromDate: handleFromDateChange,
    setToDate: handleToDateChange,
    presets,
    selectedPreset,
    setSelectedPreset,
  };
}
