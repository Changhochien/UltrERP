/**
 * ChartStateView - Shared loading/error/empty state handler for charts.
 * 
 * Provides consistent state handling across all chart surfaces:
 * - Loading: Skeleton placeholder
 * - Error: Error message with retry option
 * - Empty: Empty state message
 * - Success: Renders the chart content
 */

import type { ReactNode } from "react";

import { Button } from "../ui/button";
import { SurfaceMessage } from "../layout/PageLayout";
import { Skeleton } from "../ui/skeleton";

export interface ChartStateViewProps {
  /** Loading state */
  loading?: boolean;
  /** Error message (when in error state) */
  error?: string | null;
  /** Empty state (when no data) */
  empty?: boolean;
  /** Custom empty message content */
  emptyMessage?: ReactNode;
  /** Empty state title */
  emptyTitle?: string;
  /** Retry handler for error state */
  onRetry?: () => void;
  /** Custom height for loading skeleton */
  skeletonHeight?: number | string;
  /** The chart content to render when all states are false */
  children: ReactNode;
}

/**
 * Get locale from i18n instance.
 * Call this hook outside of the component if using with i18n.
 */
export function getResolvedLocale(i18n: { resolvedLanguage?: string; language?: string }): string {
  return i18n.resolvedLanguage ?? i18n.language ?? "en";
}

export function ChartStateView({
  loading = false,
  error = null,
  empty = false,
  emptyMessage,
  emptyTitle = "No data available",
  onRetry,
  skeletonHeight = 300,
  children,
}: ChartStateViewProps) {
  // Loading state
  if (loading) {
    return (
      <div className="space-y-3" style={{ minHeight: skeletonHeight }}>
        <Skeleton className="h-full w-full" style={{ height: skeletonHeight }} />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-3">
        <SurfaceMessage tone="danger">
          {error}
        </SurfaceMessage>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        )}
      </div>
    );
  }

  // Empty state
  if (empty) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-muted-foreground">
        {emptyMessage ?? (
          <p className="text-sm">{emptyTitle}</p>
        )}
      </div>
    );
  }

  // Success state - render chart content
  return <>{children}</>;
}
