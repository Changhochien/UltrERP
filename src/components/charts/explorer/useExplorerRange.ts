/**
 * useExplorerRange - Shared explorer range state hook.
 * 
 * Manages loaded range vs visible range state for explorer charts.
 * Provides preset navigation and visible range updates.
 */

import { useCallback, useMemo, useState } from "react";

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

    // Calculate end date (current month or available end)
    const availableEnd = new Date(availableRange.end + "-01");
    const endDate = availableEnd < currentDate ? availableEnd : currentDate;

    // Calculate start date
    const startDate = new Date(endDate);
    startDate.setMonth(startDate.getMonth() - months);
    startDate.setDate(1); // First of month

    // Ensure we don't go before available start
    const availableStart = new Date(availableRange.start + "-01");
    const finalStart = startDate < availableStart ? availableStart : startDate;

    setVisibleRange({
      start: finalStart.toISOString().slice(0, 10),
      end: endDate.toISOString().slice(0, 10),
    });
  }, [availableRange, currentDate]);

  /**
   * Update visible range directly (e.g., from brush/navigator).
   * Clears preset selection.
   */
  const updateVisibleRange = useCallback((range: ExplorerRange) => {
    setVisibleRange(range);
    setSelectedPreset(null); // Custom range
  }, []);

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
