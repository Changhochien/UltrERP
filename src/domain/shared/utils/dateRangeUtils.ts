/**
 * Date range utilities for time-series charts.
 */

/**
 * Calculate start/end months based on a preset (3M, 6M, 1Y, etc.).
 */
export function getMonthlyRangeFromPreset(preset: string): {
  startMonth: string;
  endMonth: string;
} {
  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;

  const endMonth = `${currentYear}-${String(currentMonth).padStart(2, "0")}`;
  const startMonth = getMonthBefore(endMonth, getPresetMonths(preset) - 1);

  return { startMonth, endMonth };
}

/**
 * Calculate start/end dates based on a preset (30d, 90d, etc.).
 */
export function getDateRangeFromPreset(preset: string): {
  startDate: string;
  endDate: string;
} {
  const now = new Date();
  const endDate = now.toISOString().slice(0, 10);
  const startDate = getDateBefore(endDate, getPresetDays(preset) - 1);

  return { startDate, endDate };
}

function getPresetMonths(preset: string): number {
  switch (preset) {
    case "3M": return 3;
    case "6M": return 6;
    case "1Y": return 12;
    case "2Y": return 24;
    case "4Y": return 48;
    case "All":
    default: return 48;
  }
}

function getPresetDays(preset: string): number {
  switch (preset) {
    case "30d": return 30;
    case "90d": return 90;
    case "180d": return 180;
    case "1yr": return 365;
    case "all":
    default: return 730;
  }
}

function getMonthBefore(monthStr: string, months: number): string {
  const [year, month] = monthStr.split("-").map(Number);
  let newMonth = month - months;
  let newYear = year;

  while (newMonth <= 0) {
    newMonth += 12;
    newYear -= 1;
  }

  return `${newYear}-${String(newMonth).padStart(2, "0")}`;
}

function getDateBefore(dateStr: string, days: number): string {
  const date = new Date(dateStr);
  date.setDate(date.getDate() - days);
  return date.toISOString().slice(0, 10);
}
