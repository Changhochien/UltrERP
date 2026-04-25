/**
 * ExplorerChartFrame - Explorer-tier chart wrapper component.
 * 
 * Composes:
 * - Range preset controls
 * - Detail chart
 * - Overview navigator (optional)
 * - Chart state handling
 */

import type { ReactNode } from "react";

import { ChartStateView } from "../ChartStateView";
import { RangePresetGroup } from "../controls/RangePresetGroup";
import type { PresetId } from "../controls/RangePresetGroup";
import { useExplorerRange } from "./useExplorerRange";
import { OverviewNavigator } from "./OverviewNavigator";

export interface ExplorerChartFrameProps {
  /** Chart title */
  title?: string;
  /** Chart description */
  description?: string;
  /** Loading state */
  loading?: boolean;
  /** Error message */
  error?: string | null;
  /** Whether data is empty */
  empty?: boolean;
  /** Empty message */
  emptyMessage?: string;
  /** Retry handler */
  onRetry?: () => void;
  /** Available data range from backend */
  availableRange: { start: string; end: string };
  /** Default visible range from backend */
  defaultVisibleRange: { start: string; end: string };
  /** Current visible range (controlled) */
  visibleRange?: { start: string; end: string };
  /** Visible range change handler (controlled) */
  onVisibleRangeChange?: (range: { start: string; end: string }) => void;
  /** Selected preset */
  selectedPreset?: PresetId | null;
  /** Preset change handler */
  onPresetChange?: (preset: PresetId) => void;
  /** Show overview navigator */
  showNavigator?: boolean;
  /** Chart content to render */
  children: ReactNode;
  /** Miniature overview content rendered inside the navigator */
  navigator?: ReactNode;
  /** Chart controls (mode toggle, etc.) */
  controls?: ReactNode;
  /** Additional className */
  className?: string;
}

/**
 * ExplorerChartFrame provides a complete explorer chart wrapper with:
 * - Range preset navigation
 * - Overview navigator
 * - State handling
 */
export function ExplorerChartFrame({
  title,
  description,
  loading,
  error,
  empty,
  emptyMessage,
  onRetry,
  availableRange,
  defaultVisibleRange,
  visibleRange: controlledVisibleRange,
  onVisibleRangeChange,
  selectedPreset: controlledPreset,
  onPresetChange,
  showNavigator = true,
  children,
  navigator,
  controls,
  className = "",
}: ExplorerChartFrameProps) {
  // Use controlled or internal state
  const {
    visibleRange: internalVisibleRange,
    selectedPreset: internalPreset,
    applyPreset,
    updateVisibleRange,
  } = useExplorerRange({
    availableRange,
    defaultVisibleRange,
  });

  const visibleRange = controlledVisibleRange ?? internalVisibleRange;
  const selectedPreset = controlledPreset !== undefined ? controlledPreset : internalPreset;

  const handlePresetChange = (preset: PresetId) => {
    applyPreset(preset);
    onPresetChange?.(preset);
  };

  const handleRangeChange = (range: { start: string; end: string }) => {
    updateVisibleRange(range);
    onVisibleRangeChange?.(range);
  };

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Header with title and controls */}
      {title && (
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-medium">{title}</h3>
            {description && (
              <p className="text-xs text-muted-foreground">{description}</p>
            )}
          </div>
        </div>
      )}

      {/* Preset controls */}
      <div className="flex items-center justify-between">
        <RangePresetGroup
          value={selectedPreset}
          onChange={handlePresetChange}
          aria-label="Chart time range"
        />
        {controls}
      </div>

      {/* Chart state view */}
      <ChartStateView
        loading={loading}
        error={error}
        empty={empty}
        emptyMessage={emptyMessage}
        onRetry={onRetry}
      >
        {children}
      </ChartStateView>

      {/* Overview navigator */}
      {showNavigator && !loading && !error && !empty && (
        <div className="mt-2">
          <OverviewNavigator
            loadedRange={availableRange}
            visibleRange={visibleRange}
            onRangeChange={handleRangeChange}
            height={48}
            className="rounded-lg border bg-muted/30"
          >
            {navigator ?? <div className="h-full" />}
          </OverviewNavigator>
        </div>
      )}
    </div>
  );
}
