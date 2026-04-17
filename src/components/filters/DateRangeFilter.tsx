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
  return (
    <div className="flex items-center gap-2">
      <div className="flex flex-col gap-0.5">
        <label htmlFor="date-from" className="text-xs text-muted-foreground">
          From
        </label>
        <input
          id="date-from"
          type="date"
          value={dateFrom}
          onChange={(e) => onDateFromChange(e.target.value)}
          className="h-8 rounded-md border border-input bg-background px-2 text-sm"
        />
      </div>
      <div className="flex flex-col gap-0.5">
        <label htmlFor="date-to" className="text-xs text-muted-foreground">
          To
        </label>
        <input
          id="date-to"
          type="date"
          value={dateTo}
          onChange={(e) => onDateToChange(e.target.value)}
          className="h-8 rounded-md border border-input bg-background px-2 text-sm"
        />
      </div>
    </div>
  );
}