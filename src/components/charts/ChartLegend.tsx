/**
 * ChartLegend - Shared legend component for charts.
 * 
 * Provides consistent legend display across chart surfaces.
 */

export interface ChartLegendItem {
  /** Legend label */
  label: string;
  /** Color swatch (CSS color or variable) */
  color: string;
  /** Whether this item is disabled */
  disabled?: boolean;
}

export interface ChartLegendProps {
  /** Legend items */
  items: ChartLegendItem[];
  /** Layout direction */
  direction?: "row" | "column";
  /** Additional className */
  className?: string;
}

export function ChartLegend({
  items,
  direction = "row",
  className = "",
}: ChartLegendProps) {
  return (
    <div
      role="list"
      aria-label="Chart legend"
      className={`flex flex-wrap gap-4 text-sm ${direction === "column" ? "flex-col" : ""} ${className}`}
    >
      {items.map((item, index) => (
        <div
          key={index}
          role="listitem"
          className={`flex items-center gap-2 ${item.disabled ? "opacity-50" : ""}`}
        >
          <span
            className="size-2.5 rounded-full"
            style={{ backgroundColor: item.color }}
            aria-hidden="true"
          />
          <span className="text-muted-foreground">{item.label}</span>
        </div>
      ))}
    </div>
  );
}
