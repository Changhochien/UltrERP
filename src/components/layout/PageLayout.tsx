import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../../lib/utils";
import { Badge } from "../ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: ReactNode;
  tabs?: ReactNode;
}

interface PageHeroProps {
  eyebrow?: string;
  title: string;
  description: string;
}

export function PageHero({ eyebrow, title, description }: PageHeroProps) {
  return (
    <div className="max-w-3xl space-y-4">
      {eyebrow ? (
        <div className="inline-flex items-center rounded-full border border-border/70 bg-background/55 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.32em] text-primary/80 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-sm">
          {eyebrow}
        </div>
      ) : null}
      <div className="space-y-3">
        <h1 className="text-3xl font-semibold tracking-tight text-balance text-foreground sm:text-[2.7rem] sm:leading-none">{title}</h1>
        <p className="max-w-[68ch] text-sm leading-6 text-muted-foreground sm:text-base">{description}</p>
      </div>
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, actions, tabs }: PageHeaderProps) {
  return (
    <Card className="surface-hero relative overflow-hidden border-border/70 shadow-[0_34px_90px_-64px_rgba(15,23,42,0.78)]">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -right-16 top-0 h-40 w-40 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute left-0 top-0 h-px w-full bg-white/8" />
      </div>
      <CardContent className="relative p-0">
        <div className="flex flex-col gap-8 p-6 sm:p-8 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0 flex-1">
            <PageHero eyebrow={eyebrow} title={title} description={description} />
          </div>
          {actions ? (
            <div className="w-full rounded-[1.75rem] border border-border/70 bg-background/58 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-md xl:w-auto xl:max-w-[34rem]">
              <div className="flex w-full flex-wrap items-center gap-3">
                {actions}
              </div>
            </div>
          ) : null}
        </div>
        {tabs ? <div className="border-t border-border/55 bg-background/26 backdrop-blur-sm">{tabs}</div> : null}
      </CardContent>
    </Card>
  );
}

interface SectionCardProps {
  title?: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
  contentClassName?: string;
  children?: ReactNode;
}

export function SectionCard({ title, description, actions, className, contentClassName, children }: SectionCardProps) {
  return (
    <Card className={className}>
      {title || description || actions ? (
        <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1">
            {title ? <CardTitle>{title}</CardTitle> : null}
            {description ? <CardDescription>{description}</CardDescription> : null}
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
        </CardHeader>
      ) : null}
      <CardContent className={cn(title || description || actions ? "pt-0" : "pt-6", contentClassName)}>
        {children}
      </CardContent>
    </Card>
  );
}

interface MetricCardProps {
  title: string;
  value: string;
  description: string;
  trendLabel?: string;
  trendDirection?: "up" | "down" | "flat";
  points?: number[];
  badge?: ReactNode;
}

function MetricSparkline({ points }: { points: number[] }) {
  if (points.length < 2) {
    return <div className="h-12 rounded-xl bg-muted/50" />;
  }

  const max = Math.max(...points);
  const min = Math.min(...points);
  const range = max - min || 1;
  const step = 100 / (points.length - 1);
  const coordinates = points
    .map((point, index) => {
      const x = index * step;
      const y = 40 - ((point - min) / range) * 34;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg viewBox="0 0 100 40" className="h-12 w-full text-primary" preserveAspectRatio="none" aria-hidden="true">
      <polyline fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" points={coordinates} />
    </svg>
  );
}

export function MetricCard({ title, value, description, trendLabel, trendDirection = "flat", points = [], badge }: MetricCardProps) {
  const trendIcon = trendDirection === "up"
    ? <ArrowUpRight className="size-4" />
    : trendDirection === "down"
      ? <ArrowDownRight className="size-4" />
      : <Minus className="size-4" />;
  const trendVariant = trendDirection === "up" ? "success" : trendDirection === "down" ? "destructive" : "neutral";

  return (
    <Card className="border-border/80 bg-card/90">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">{title}</p>
            <div className="text-3xl font-semibold tracking-tight">{value}</div>
          </div>
          {badge}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">{description}</p>
        {points.length > 0 ? <MetricSparkline points={points} /> : null}
        {trendLabel ? (
          <Badge variant={trendVariant} className="gap-1.5 normal-case tracking-normal">
            {trendIcon}
            {trendLabel}
          </Badge>
        ) : null}
      </CardContent>
    </Card>
  );
}

interface PaginationBarProps {
  page: number;
  totalLabel: string;
  onPrev?: () => void;
  onNext?: () => void;
  prevLabel?: string;
  nextLabel?: string;
}

export function PaginationBar({
  page,
  totalLabel,
  onPrev,
  onNext,
  prevLabel = "Previous",
  nextLabel = "Next",
}: PaginationBarProps) {
  return (
    <div className="flex flex-col gap-3 border-t border-border/70 pt-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
      <span>Page {page} · {totalLabel}</span>
      <div className="flex items-center gap-2">
        {onPrev ? (
          <button type="button" onClick={onPrev}>
            {prevLabel}
          </button>
        ) : null}
        {onNext ? (
          <button type="button" onClick={onNext}>
            {nextLabel}
          </button>
        ) : null}
      </div>
    </div>
  );
}

interface SurfaceMessageProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  tone?: "default" | "danger" | "success" | "warning";
}

export function SurfaceMessage({ children, tone = "default", className, ...props }: SurfaceMessageProps) {
  return (
    <div
      className={cn(
        "rounded-xl border px-4 py-3 text-sm",
        tone === "danger" && "tone-destructive",
        tone === "success" && "tone-success",
        tone === "warning" && "tone-warning",
        tone === "default" && "border-border bg-muted/40 text-muted-foreground",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export { PageTabs } from "./PageTabs";
export type { PageTabItem } from "./PageTabs";
