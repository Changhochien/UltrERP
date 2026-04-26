import { format } from "date-fns"
import { enUS, zhTW } from "date-fns/locale"
import type { Locale } from "date-fns/locale"
import type { DateRange } from "react-day-picker"

import { parseBackendDate } from "@/lib/time"

function parseLocalCalendarDate(value: string): Date {
  const [year, month, day] = value.split("-").map((segment) => Number(segment))

  return new Date(year, month - 1, day)
}

export function getDatePickerLocale(language?: string): Locale {
  return language === "zh-Hant" ? zhTW : enUS
}

export function formatDatePickerValue(
  value: Date | undefined,
  language?: string
): string {
  if (!value) {
    return ""
  }
  const pattern = language === "zh-Hant" ? "PPP" : "PP"

  return format(value, pattern, { locale: getDatePickerLocale(language) })
}

export function formatDateRangePickerValue(
  value: DateRange | undefined,
  language?: string
): string {
  if (!value?.from && !value?.to) {
    return ""
  }

  if (value?.from && value?.to) {
    return `${formatDatePickerValue(value.from, language)} - ${formatDatePickerValue(
      value.to,
      language
    )}`
  }

  return formatDatePickerValue(value?.from ?? value?.to, language)
}

export function parseDatePickerInputValue(
  value: string | null | undefined
): Date | undefined {
  if (!value) {
    return undefined
  }

  return /^\d{4}-\d{2}-\d{2}$/.test(value)
    ? parseLocalCalendarDate(value)
    : parseBackendDate(value)
}

export function serializeDatePickerValue(value: Date | null | undefined): string {
  if (!value) {
    return ""
  }

  return format(value, "yyyy-MM-dd")
}