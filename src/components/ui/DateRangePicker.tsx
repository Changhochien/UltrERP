import * as React from "react"
import { DayPicker, type DateRange } from "react-day-picker"
import "react-day-picker/style.css"
import { CalendarRange } from "lucide-react"
import { useTranslation } from "react-i18next"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  formatDateRangePickerValue,
  getDatePickerLocale,
} from "@/components/ui/date-picker-utils"

const triggerClassName =
  "flex h-8 w-full min-w-0 items-center justify-between gap-2 rounded-lg border border-input bg-transparent px-2.5 py-1 text-left text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-input/50 disabled:opacity-50"

export interface DateRangePickerProps
  extends Omit<React.ComponentPropsWithoutRef<"button">, "onChange" | "value"> {
  value?: DateRange
  onChange: (value: DateRange | undefined) => void
  placeholder?: string
  defaultMonth?: Date
  allowClear?: boolean
}

export function DateRangePicker({
  className,
  value,
  onChange,
  placeholder,
  defaultMonth,
  allowClear = true,
  disabled,
  ...props
}: DateRangePickerProps) {
  const { i18n, t } = useTranslation("common")
  const [open, setOpen] = React.useState(false)
  const [selectionAnchor, setSelectionAnchor] = React.useState<Date | null>(null)
  const [month, setMonth] = React.useState<Date>(
    value?.from ?? value?.to ?? defaultMonth ?? new Date()
  )
  const language = i18n.language || i18n.resolvedLanguage
  const resolvedPlaceholder = placeholder ?? t("dateRangePicker.placeholder")

  React.useEffect(() => {
    if (value?.from || value?.to) {
      setMonth(value?.from ?? value?.to ?? new Date())
      return
    }

    if (defaultMonth) {
      setMonth(defaultMonth)
    }
  }, [defaultMonth, value?.from, value?.to])

  const displayValue = formatDateRangePickerValue(
    value,
    language
  )

  return (
    <Popover
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen)
        if (nextOpen) {
          setSelectionAnchor(null)
          setMonth(value?.from ?? value?.to ?? defaultMonth ?? new Date())
        }
      }}
    >
      <PopoverTrigger
        render={
          <button
            type="button"
            disabled={disabled}
            className={cn(triggerClassName, !value?.from && !value?.to && "text-muted-foreground", className)}
            {...props}
          />
        }
      >
        <span className="truncate">{displayValue || resolvedPlaceholder}</span>
        <CalendarRange className="size-4 shrink-0 text-muted-foreground" />
      </PopoverTrigger>
      <PopoverContent align="start" sideOffset={6} className="w-auto p-3">
        <DayPicker
          mode="range"
          month={month}
          onMonthChange={setMonth}
          selected={value}
          locale={getDatePickerLocale(language)}
          onSelect={(nextValue) => {
            onChange(nextValue)

            if (nextValue?.from) {
              setMonth(nextValue.from)
            }

            if (nextValue?.from && selectionAnchor === null) {
              setSelectionAnchor(nextValue.from)
              return
            }

            if (nextValue?.from && nextValue?.to) {
              setOpen(false)
              setSelectionAnchor(null)
              return
            }

            setSelectionAnchor(nextValue?.from ?? null)
          }}
        />
        {allowClear && (value?.from || value?.to) ? (
          <div className="flex justify-end border-t border-border pt-2">
            <Button
              type="button"
              variant="ghost"
              size="xs"
              onClick={() => {
                onChange(undefined)
                setOpen(false)
                setSelectionAnchor(null)
              }}
            >
              {t("datePicker.clear")}
            </Button>
          </div>
        ) : null}
      </PopoverContent>
    </Popover>
  )
}