/**
 * useExplorerRange - Shared explorer range state hook.
 * 
 * Manages loaded range vs visible range state for explorer charts.
 * Provides preset navigation and visible range updates.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import type { PresetId } from "../controls/RangePresetGroup";
import { presetToMonths } from "../controls/RangePresetGroup";

export interface ExplorerRange {
  start: string; // ISO date YYYY-MM-DD or YYYY-MM
  end: string;
}

export interface UseExplorerRangeOptions {
  /** Available range from backend (data bounds) */
  availableRange: ExplorerRange;
  /** Default visible range (from backend metadata) */
  defaultVisibleRange: ExplorerRange;
  /** Available presets */
  presets?: PresetId[];
  /** Current date for "All" preset calculation */
  currentDate?: Date;
}

export interface UseExplorerRangeReturn {
  /** Full data window from backend */
  loadedRange: ExplorerRange;
  /** User's current viewport */
  visibleRange: ExplorerRange;
  /** Currently selected preset (null if custom range) */
  selectedPreset: PresetId | null;
  /** Navigation actions */
  applyPreset: (preset: PresetId) => void;
  updateVisibleRange: (range: ExplorerRange) => void;
  reset: () => void;
  /** Helper to get month count from preset */
  getPresetMonths: (preset: PresetId) => number | null;
}

function isMonthRange(range: ExplorerRange): boolean {
  return range.start.length === 7 && range.end.length === 7;
}

function parseRangeDate(value: string): Date {
  return new Date(value.length === 7 ? `${value}-01T00:00:00Z` : `${value}T00:00:00Z`);
}

function formatRangeDate(date: Date, monthPrecision: boolean): string {
  const isoDate = date.toISOString().slice(0, 10);
  return monthPrecision ? isoDate.slice(0, 7) : isoDate;
}

function clampRange(range: ExplorerRange, bounds: ExplorerRange): ExplorerRange {
  const rangeStart = parseRangeDate(range.start).getTime();
  const rangeEnd = parseRangeDate(range.end).getTime();
  const boundsStart = parseRangeDate(bounds.start).getTime();
  const boundsEnd = parseRangeDate(bounds.end).getTime();
  const monthPrecision = isMonthRange(bounds);

  const start = new Date(Math.max(boundsStart, Math.min(rangeStart, boundsEnd)));
  const end = new Date(Math.max(start.getTime(), Math.min(rangeEnd, boundsEnd)));

  return {
    start: formatRangeDate(start, monthPrecision),
    end: formatRangeDate(end, monthPrecision),
  };
}

/**
 * Hook for managing explorer chart range state.
 */
export function useExplorerRange({
  availableRange,
  defaultVisibleRange,
  presets: _presets = ["3M", "6M", "1Y", "2Y", "4Y", "All"],
  currentDate = new Date(),
}: UseExplorerRangeOptions): UseExplorerRangeReturn {
  // Loaded range is fixed to available data bounds
  const loadedRange = useMemo(() => availableRange, [availableRange]);

  // Visible range starts at default
  const [visibleRange, setVisibleRange] = useState<ExplorerRange>(defaultVisibleRange);

  // Currently selected preset (null if user customized)
  const [selectedPreset, setSelectedPreset] = useState<PresetId | null>("1Y");

  useEffect(() => {
    setVisibleRange(clampRange(defaultVisibleRange, availableRange));
    setSelectedPreset("1Y");
  }, [
    availableRange.start,
    availableRange.end,
    defaultVisibleRange.start,
    defaultVisibleRange.end,
  ]);

  /**
   * Apply a preset, updating the visible range.
   */
  const applyPreset = useCallback((preset: PresetId) => {
    setSelectedPreset(preset);

    if (preset === "All") {
      // Show full available range
      setVisibleRange(availableRange);
      return;
    }

    const months = presetToMonths(preset);
    if (months === null) {
      setVisibleRange(availableRange);
      return;
    }

    const monthPrecision = isMonthRange(availableRange);
    const availableEnd = parseRangeDate(availableRange.end);
    const availableStart = parseRangeDate(availableRange.start);
    const currentRangeDate = monthPrecision
      ? new Date(Date.UTC(currentDate.getUTCFullYear(), currentDate.getUTCMonth(), 1))
      : new Date(Date.UTC(currentDate.getUTCFullYear(), currentDate.getUTCMonth(), currentDate.getUTCDate()));
    const endDate = availableEnd < currentRangeDate ? availableEnd : currentRangeDate;

    // Calculate start date
    const startDate = new Date(endDate);
    if (monthPrecision) {
      startDate.setUTCMonth(startDate.getUTCMonth() - (months - 1));
      startDate.setUTCDate(1);
    } else {
      startDate.setUTCMonth(startDate.getUTCMonth() - months);
    }

    // Ensure we don't go before available start
    const finalStart = startDate < availableStart ? availableStart : startDate;

    setVisibleRange({
      start: formatRangeDate(finalStart, monthPrecision),
      end: formatRangeDate(endDate, monthPrecision),
    });
  }, [availableRange, currentDate]);

  /**
   * Update visible range directly (e.g., from brush/navigator).
   * Clears preset selection.
   */
  const updateVisibleRange = useCallback((range: ExplorerRange) => {
    setVisibleRange(clampRange(range, availableRange));
    setSelectedPreset(null); // Custom range
  }, [availableRange]);

  /**
   * Reset to default visible range.
   */
  const reset = useCallback(() => {
    setVisibleRange(defaultVisibleRange);
    setSelectedPreset("1Y");
  }, [defaultVisibleRange]);

  /**
   * Get month count for a preset.
   */
  const getPresetMonths = useCallback((preset: PresetId): number | null => {
    return presetToMonths(preset);
  }, []);

  return {
    loadedRange,
    visibleRange,
    selectedPreset,
    applyPreset,
    updateVisibleRange,
    reset,
    getPresetMonths,
  };
}
