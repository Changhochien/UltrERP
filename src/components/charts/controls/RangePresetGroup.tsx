/**
 * RangePresetGroup - Shared preset period button group for charts.
 * 
 * Standardized period selector for chart surfaces.
 * Supports accessibility with aria-pressed and keyboard navigation.
 */



import { Button } from "../../ui/button";

export type PresetId = "3M" | "6M" | "1Y" | "2Y" | "4Y" | "All";

export interface RangePreset {
  id: PresetId;
  label: string;
  /** Optional number of months (for All, use undefined) */
  months?: number;
}

export interface RangePresetGroupProps {
  /** Available presets to show */
  presets?: RangePreset[];
  /** Currently selected preset */
  value?: PresetId | null;
  /** Selection change handler */
  onChange: (preset: PresetId) => void;
  /** ARIA label for the group */
  "aria-label"?: string;
  /** Additional className */
  className?: string;
  /** Button size variant */
  size?: "sm" | "default" | "lg";
}

const DEFAULT_PRESETS: RangePreset[] = [
  { id: "3M", label: "3M", months: 3 },
  { id: "6M", label: "6M", months: 6 },
  { id: "1Y", label: "1Y", months: 12 },
  { id: "2Y", label: "2Y", months: 24 },
  { id: "4Y", label: "4Y", months: 48 },
  { id: "All", label: "All" },
];

export function RangePresetGroup({
  presets = DEFAULT_PRESETS,
  value,
  onChange,
  "aria-label": ariaLabel = "Time range preset",
  className = "",
  size = "sm",
}: RangePresetGroupProps) {
  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={`flex items-center gap-1 ${className}`}
    >
      {presets.map((preset) => (
        <Button
          key={preset.id}
          type="button"
          size={size}
          variant={value === preset.id ? "default" : "ghost"}
          onClick={() => onChange(preset.id)}
          aria-pressed={value === preset.id}
        >
          {preset.label}
        </Button>
      ))}
    </div>
  );
}

/**
 * Convert preset ID to month count (or null for "All").
 */
export function presetToMonths(preset: PresetId): number | null {
  switch (preset) {
    case "3M": return 3;
    case "6M": return 6;
    case "1Y": return 12;
    case "2Y": return 24;
    case "4Y": return 48;
    case "All": return null;
  }
}
