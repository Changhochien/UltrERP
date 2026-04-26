/**
 * Calendar component using react-day-picker.
 */

import { DayPicker, type DayPickerProps } from "react-day-picker";

export type { DayPickerProps as CalendarProps };

export function Calendar(props: DayPickerProps) {
  return <DayPicker {...props} />;
}
