import * as React from "react";

import { cn } from "@/lib/utils";

import { Badge, type BadgeProps } from "./badge";

export type StatusBadgeVariant = Extract<
  NonNullable<BadgeProps["variant"]>,
  "neutral" | "info" | "success" | "warning" | "destructive"
>;

export type StatusBadgeOverrides = Partial<Record<string, StatusBadgeVariant>>;

const KNOWN_STATUS_VARIANTS: Record<string, StatusBadgeVariant> = {
  acknowledged: "success",
  acked: "success",
  active: "success",
  approved: "success",
  cancelled: "destructive",
  canceled: "destructive",
  dead_letter: "destructive",
  dismissed: "destructive",
  draft: "neutral",
  failed: "destructive",
  fulfilled: "success",
  in_progress: "info",
  inactive: "neutral",
  open: "warning",
  overdue: "destructive",
  paid: "success",
  partial: "warning",
  partially_received: "warning",
  pending: "neutral",
  queued: "info",
  received: "success",
  resolved: "success",
  retrying: "warning",
  sent: "info",
  shipped: "info",
  snoozed: "warning",
  submitted: "warning",
  unpaid: "neutral",
  voided: "destructive",
};

function normalizeStatus(status?: string | null) {
  return (status ?? "").trim().toLowerCase();
}

export function humanizeStatusLabel(status?: string | null) {
  const normalized = normalizeStatus(status);
  if (!normalized) {
    return "Unknown";
  }

  return normalized
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

export function resolveStatusBadgeVariant(
  status?: string | null,
  options?: {
    defaultVariant?: StatusBadgeVariant;
    overrides?: StatusBadgeOverrides;
  },
) {
  const normalized = normalizeStatus(status);

  if (!normalized) {
    return options?.defaultVariant ?? "neutral";
  }

  return (
    options?.overrides?.[normalized] ??
    KNOWN_STATUS_VARIANTS[normalized] ??
    options?.defaultVariant ??
    "neutral"
  );
}

export interface StatusBadgeProps
  extends Omit<BadgeProps, "children" | "variant"> {
  status?: string | null;
  label?: React.ReactNode;
  defaultVariant?: StatusBadgeVariant;
  overrides?: StatusBadgeOverrides;
}

export function StatusBadge({
  className,
  defaultVariant = "neutral",
  label,
  overrides,
  status,
  ...props
}: StatusBadgeProps) {
  return (
    <Badge
      variant={resolveStatusBadgeVariant(status, { defaultVariant, overrides })}
      className={cn("normal-case tracking-normal", className)}
      {...props}
    >
      {label ?? humanizeStatusLabel(status)}
    </Badge>
  );
}