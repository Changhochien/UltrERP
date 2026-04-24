/**
 * OverviewNavigator - Overview chart with visible range selection.
 * 
 * Shows a miniature version of the full data range with a draggable
 * selection window for visible range control.
 */

import type { ReactElement } from "react";

import { useMemo, useRef, useState } from "react";

import type { ExplorerRange } from "./useExplorerRange";

export interface OverviewNavigatorProps {
  /** Full loaded data range */
  loadedRange: ExplorerRange;
  /** Current visible range */
  visibleRange: ExplorerRange;
  /** Miniature chart to render (receives width) */
  children: ReactElement;
  /** Called when visible range changes */
  onRangeChange: (range: ExplorerRange) => void;
  /** Height of the overview strip */
  height?: number;
  /** Additional className */
  className?: string;
}

/**
 * OverviewNavigator provides a brush-like selection over a miniature chart.
 */
export function OverviewNavigator({
  loadedRange,
  visibleRange,
  children,
  onRangeChange,
  height = 40,
  className = "",
}: OverviewNavigatorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragType, setDragType] = useState<"move" | "left" | "right" | null>(null);
  const [dragStartX, setDragStartX] = useState(0);
  const [dragStartRange, setDragStartRange] = useState<ExplorerRange | null>(null);

  // Calculate pixel positions from dates
  const { left, width } = useMemo(() => {
    const loadedStart = new Date(loadedRange.start).getTime();
    const loadedEnd = new Date(loadedRange.end).getTime();
    const loadedDuration = loadedEnd - loadedStart;

    const toPercent = (date: string) => {
      const t = new Date(date).getTime();
      return ((t - loadedStart) / loadedDuration) * 100;
    };

    return {
      left: toPercent(visibleRange.start),
      width: toPercent(visibleRange.end) - toPercent(visibleRange.start),
    };
  }, [loadedRange, visibleRange]);

  const handleMouseDown = (e: React.MouseEvent, type: "move" | "left" | "right") => {
    e.preventDefault();
    setIsDragging(true);
    setDragType(type);
    setDragStartX(e.clientX);
    setDragStartRange({ ...visibleRange });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !dragStartRange || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const dx = e.clientX - dragStartX;
    const dxPercent = (dx / rect.width) * 100;

    const loadedStart = new Date(loadedRange.start);
    const loadedEnd = new Date(loadedRange.end);
    const loadedDuration = loadedEnd.getTime() - loadedStart.getTime();

    // Convert pixel delta to date delta
    const dateDelta = (dxPercent / 100) * loadedDuration;

    let newStart = dragStartRange.start;
    let newEnd = dragStartRange.end;

    if (dragType === "move") {
      const startTime = new Date(dragStartRange.start).getTime() + dateDelta;
      const endTime = new Date(dragStartRange.end).getTime() + dateDelta;

      // Clamp to loaded range
      if (startTime >= loadedStart.getTime() && endTime <= loadedEnd.getTime()) {
        newStart = new Date(startTime).toISOString().slice(0, 10);
        newEnd = new Date(endTime).toISOString().slice(0, 10);
      }
    } else if (dragType === "left") {
      const startTime = Math.max(
        loadedStart.getTime(),
        new Date(dragStartRange.start).getTime() + dateDelta
      );
      // Don't let left go past right
      const endTime = new Date(dragStartRange.end).getTime();
      if (startTime < endTime) {
        newStart = new Date(startTime).toISOString().slice(0, 10);
      }
    } else if (dragType === "right") {
      const endTime = Math.min(
        loadedEnd.getTime(),
        new Date(dragStartRange.end).getTime() + dateDelta
      );
      // Don't let right go past left
      const startTime = new Date(dragStartRange.start).getTime();
      if (endTime > startTime) {
        newEnd = new Date(endTime).toISOString().slice(0, 10);
      }
    }

    if (newStart !== visibleRange.start || newEnd !== visibleRange.end) {
      onRangeChange({ start: newStart, end: newEnd });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setDragType(null);
  };

  return (
    <div
      ref={containerRef}
      className={`relative select-none ${className}`}
      style={{ height }}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Miniature chart */}
      <div className="absolute inset-0 overflow-hidden opacity-50">
        {children}
      </div>

      {/* Selection overlay */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{ cursor: isDragging ? "grabbing" : "default" }}
      >
        {/* Dimmed regions */}
        <div
          className="absolute top-0 h-full bg-black/20"
          style={{ left: 0, width: `${left}%` }}
        />
        <div
          className="absolute top-0 h-full bg-black/20"
          style={{ left: `${left + width}%`, right: 0 }}
        />

        {/* Selection window */}
        <div
          className="absolute top-0 h-full border-y-2 border-primary bg-transparent"
          style={{ left: `${left}%`, width: `${width}%` }}
        >
          {/* Left handle */}
          <div
            className="absolute -left-1 top-0 h-full w-2 cursor-ew-resize bg-primary"
            onMouseDown={(e) => handleMouseDown(e, "left")}
          />

          {/* Right handle */}
          <div
            className="absolute -right-1 top-0 h-full w-2 cursor-ew-resize bg-primary"
            onMouseDown={(e) => handleMouseDown(e, "right")}
          />

          {/* Move handle (center) */}
          <div
            className="absolute inset-x-2 top-0 h-full cursor-grab active:cursor-grabbing"
            onMouseDown={(e) => handleMouseDown(e, "move")}
          />
        </div>
      </div>
    </div>
  );
}
