import * as React from "react"
import { DayPicker } from "react-day-picker"
import "react-day-picker/style.css"
import { CalendarDays } from "lucide-react"
import { useTranslation } from "react-i18next"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  formatDatePickerValue,
  getDatePickerLocale,
} from "@/components/ui/date-picker-utils"

const triggerClassName =
  "flex h-8 w-full min-w-0 items-center justify-between gap-2 rounded-lg border border-input bg-transparent px-2.5 py-1 text-left text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-input/50 disabled:opacity-50"

export interface DatePickerProps
  extends Omit<React.ComponentPropsWithoutRef<"button">, "onChange" | "value"> {
  value?: Date
  onChange: (value: Date | undefined) => void
  placeholder?: string
  defaultMonth?: Date
  allowClear?: boolean
}

export function DatePicker({
  className,
  value,
  onChange,
  placeholder,
  defaultMonth,
  allowClear = true,
  disabled,
  ...props
}: DatePickerProps) {
  const { i18n, t } = useTranslation("common")
  const [open, setOpen] = React.useState(false)
  const [month, setMonth] = React.useState<Date>(value ?? defaultMonth ?? new Date())
  const language = i18n?.language || i18n?.resolvedLanguage || "en"
  const resolvedPlaceholder = placeholder ?? t("datePicker.placeholder")

  React.useEffect(() => {
    if (value) {
      setMonth(value)
      return
    }

    if (defaultMonth) {
      setMonth(defaultMonth)
    }
  }, [defaultMonth, value])

  const displayValue = formatDatePickerValue(value, language)

  return (
    <Popover
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen)
        if (nextOpen) {
          setMonth(value ?? defaultMonth ?? new Date())
        }
      }}
    >
      <PopoverTrigger
        render={
          <button
            type="button"
            disabled={disabled}
            className={cn(triggerClassName, !value && "text-muted-foreground", className)}
            {...props}
          />
        }
      >
        <span className="truncate">{displayValue || resolvedPlaceholder}</span>
        <CalendarDays className="size-4 shrink-0 text-muted-foreground" />
      </PopoverTrigger>
      <PopoverContent align="start" sideOffset={6} className="w-auto p-3">
        <DayPicker
          mode="single"
          month={month}
          onMonthChange={setMonth}
          selected={value}
          locale={getDatePickerLocale(language)}
          onSelect={(nextValue) => {
            onChange(nextValue)
            if (nextValue) {
              setMonth(nextValue)
              setOpen(false)
            }
          }}
        />
        {allowClear && value ? (
          <div className="flex justify-end border-t border-border pt-2">
            <Button
              type="button"
              variant="ghost"
              size="xs"
              onClick={() => {
                onChange(undefined)
                setOpen(false)
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