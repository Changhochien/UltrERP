/**
 * Calendar component using react-day-picker.
 */

import { DayPicker } from "react-day-picker";
import type { DayPickerProps } from "react-day-picker";

export interface CalendarProps extends DayPickerProps {
  mode?: "single" | "multiple" | "range";
}

export function Calendar(props: CalendarProps) {
  return <DayPicker {...props} />;
}
