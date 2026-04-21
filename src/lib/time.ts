/** Time / timezone utilities — all date parsing and formatting goes through here.
 *
 * All backend dates are UTC ISO-8601 strings ("2026-01-15T08:30:00Z") representing
 * midnight UTC (i.e. "Asia/Taipei" date the server intended).
 *
 * Because JavaScript Date treats a bare "YYYY-MM-DD" string as UTC midnight but a
 * full ISO string as local midnight, we normalise by appending "T00:00:00Z" so that
 * the same calendar date is consistently parsed regardless of browser TZ.
 */

import { format } from "date-fns";
import { zhTW } from "date-fns/locale";

const DATE_ONLY_RE = /^\d{4}-\d{2}-\d{2}$/;

/** Canonical business timezone for UltrERP — Taiwan. */
export const TIMEZONE = "Asia/Taipei";

// Injected by tests or dev tools. Defaults to real clock.
let _now: () => Date = () => new Date();

function formatDatePartsInTimezone(value: Date, timeZone: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(value);

  const year = parts.find((part) => part.type === "year")?.value;
  const month = parts.find((part) => part.type === "month")?.value;
  const day = parts.find((part) => part.type === "day")?.value;

  if (!year || !month || !day) {
    return format(value, "yyyy-MM-dd");
  }

  return `${year}-${month}-${day}`;
}

export function setAppTimeGetter(fn: () => Date): void {
  _now = fn;
}

export function appNow(): Date {
  return _now();
}

/** Returns today's date as ISO string "YYYY-MM-DD" in Taiwan time */
export function appTodayISO(): string {
  return formatDatePartsInTimezone(_now(), TIMEZONE);
}

/** Parse a backend date string that may be date-only ("YYYY-MM-DD") or
 * full ISO ("YYYY-MM-DDTHH:MM:SSZ") into a local-time Date at midnight.
 * This ensures the date component always matches what the server recorded,
 * not what the browser's TZ offset would shift it to.
 */
export function parseBackendDate(isoOrDateStr: string): Date {
  const normalised = DATE_ONLY_RE.test(isoOrDateStr)
    ? `${isoOrDateStr}T00:00:00Z`
    : isoOrDateStr;
  return new Date(normalised);
}

/** Format backend calendar dates without letting browser timezone shift date-only values. */
export function formatBackendCalendarDate(
  isoOrDateStr: string,
  pattern: "MM/dd" | "yyyy-MM-dd",
): string {
  if (DATE_ONLY_RE.test(isoOrDateStr)) {
    return pattern === "MM/dd"
      ? isoOrDateStr.slice(5).replace("-", "/")
      : isoOrDateStr;
  }

  const parsed = parseBackendDate(isoOrDateStr);
  return Number.isNaN(parsed.getTime()) ? "" : format(parsed, pattern);
}

/** Format a UTC ISO date string for display in Taiwan timezone */
export function formatForDisplay(utcIsoStr: string): string {
  return format(parseBackendDate(utcIsoStr), "yyyy/MM/dd", { locale: zhTW });
}

/** Format a UTC ISO date string with time for display in Taiwan timezone */
export function formatForDisplayWithTime(utcIsoStr: string): string {
  return format(parseBackendDate(utcIsoStr), "yyyy/MM/dd HH:mm", { locale: zhTW });
}
