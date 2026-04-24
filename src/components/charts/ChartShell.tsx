/**
 * ChartShell - Shared section/card wrapper for charts.
 * 
 * Provides consistent wrapper around chart surfaces:
 * - Optional title and description
 * - Optional action controls (period buttons, mode toggles)
 * - Supports both Card and SectionCard hosting patterns
 * 
 * For simple charts, use Card. For dashboard sections, use SectionCard.
 */

import type { ReactNode } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";

export interface ChartShellProps {
  /** Chart title */
  title?: string;
  /** Chart description */
  description?: string;
  /** Action controls (buttons, toggles) */
  controls?: ReactNode;
  /** Whether to use SectionCard instead of Card */
  useSectionCard?: boolean;
  /** Additional className for the card */
  className?: string;
  /** Additional className for content */
  contentClassName?: string;
  /** Chart content */
  children: ReactNode;
}

/**
 * ChartShell wraps chart content in a consistent card structure.
 */
export function ChartShell({
  title,
  description,
  controls,
  useSectionCard = false,
  className,
  contentClassName,
  children,
}: ChartShellProps) {
  // Use SectionCard pattern (matches existing dashboard/intelligence surfaces)
  if (useSectionCard) {
    return (
      <Card className={className}>
        {(title || description || controls) && (
          <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-1">
              {title && <CardTitle>{title}</CardTitle>}
              {description && <CardDescription>{description}</CardDescription>}
            </div>
            {controls && <div className="flex flex-wrap items-center gap-2">{controls}</div>}
          </CardHeader>
        )}
        <CardContent className={title || description || controls ? "pt-0" : undefined}>
          {children}
        </CardContent>
      </Card>
    );
  }

  // Use simple Card pattern
  return (
    <Card className={className}>
      {(title || description || controls) && (
        <CardHeader className="flex flex-row items-start justify-between gap-4 pb-2">
          <div className="space-y-1">
            {title && <CardTitle>{title}</CardTitle>}
            {description && <CardDescription>{description}</CardDescription>}
          </div>
          {controls && <div className="flex flex-wrap items-center gap-2">{controls}</div>}
        </CardHeader>
      )}
      <CardContent className={contentClassName}>
        {children}
      </CardContent>
    </Card>
  );
}
