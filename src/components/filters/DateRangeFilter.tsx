import { useTranslation } from "react-i18next";

import { DatePicker } from "@/components/ui/DatePicker";
import {
  parseDatePickerInputValue,
  serializeDatePickerValue,
} from "@/components/ui/date-picker-utils";

interface DateRangeFilterProps {
  dateFrom: string;
  dateTo: string;
  onDateFromChange: (value: string) => void;
  onDateToChange: (value: string) => void;
}

export function DateRangeFilter({
  dateFrom,
  dateTo,
  onDateFromChange,
  onDateToChange,
}: DateRangeFilterProps) {
  const { t } = useTranslation("common");

  return (
    <div className="flex min-w-56 flex-col gap-1">
      <span className="text-xs text-muted-foreground">{t("dateRangeFilter.label")}</span>
      <div className="grid gap-2 sm:grid-cols-2">
        <label htmlFor="date-range-from" className="flex min-w-0 flex-col gap-1">
          <span className="text-xs text-muted-foreground">{t("dateRangeFilter.from")}</span>
          <DatePicker
            id="date-range-from"
            aria-label={t("dateRangeFilter.fromAria")}
            placeholder={t("dateRangeFilter.from")}
            value={parseDatePickerInputValue(dateFrom)}
            onChange={(value) => onDateFromChange(serializeDatePickerValue(value))}
            className="min-w-0"
          />
        </label>
        <label htmlFor="date-range-to" className="flex min-w-0 flex-col gap-1">
          <span className="text-xs text-muted-foreground">{t("dateRangeFilter.to")}</span>
          <DatePicker
            id="date-range-to"
            aria-label={t("dateRangeFilter.toAria")}
            placeholder={t("dateRangeFilter.to")}
            value={parseDatePickerInputValue(dateTo)}
            onChange={(value) => onDateToChange(serializeDatePickerValue(value))}
            className="min-w-0"
          />
        </label>
      </div>
    </div>
  );
}