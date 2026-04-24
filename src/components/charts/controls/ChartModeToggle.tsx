/**
 * ChartModeToggle - Shared bar/line mode toggle for charts.
 * 
 * Standardized toggle for switching chart display modes.
 * Supports accessibility with aria-pressed and keyboard navigation.
 */

import type { ReactNode } from "react";

import { Button } from "../../ui/button";

export type ChartMode = "bar" | "line";

export interface ChartModeOption {
  mode: ChartMode;
  label: string;
  icon?: ReactNode;
}

export interface ChartModeToggleProps {
  /** Available mode options */
  options?: ChartModeOption[];
  /** Currently selected mode */
  value: ChartMode;
  /** Selection change handler */
  onChange: (mode: ChartMode) => void;
  /** ARIA label for the toggle */
  "aria-label"?: string;
  /** Additional className */
  className?: string;
  /** Button size variant */
  size?: "sm" | "default" | "lg";
}

const DEFAULT_OPTIONS: ChartModeOption[] = [
  { mode: "bar", label: "Bar" },
  { mode: "line", label: "Line" },
];

export function ChartModeToggle({
  options = DEFAULT_OPTIONS,
  value,
  onChange,
  "aria-label": ariaLabel = "Chart display mode",
  className = "",
  size = "sm",
}: ChartModeToggleProps) {
  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={`inline-flex items-center rounded-md border p-0.5 ${className}`}
    >
      {options.map((option) => (
        <Button
          key={option.mode}
          type="button"
          size={size}
          variant="ghost"
          className={`
            rounded-sm px-3 py-1.5 text-xs font-medium transition-colors
            ${value === option.mode 
              ? "bg-background text-foreground shadow-sm" 
              : "text-muted-foreground hover:text-foreground"
            }
          `}
          onClick={() => onChange(option.mode)}
          aria-pressed={value === option.mode}
        >
          {option.icon && <span className="mr-1.5">{option.icon}</span>}
          {option.label}
        </Button>
      ))}
    </div>
  );
}
