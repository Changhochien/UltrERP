"use client";

import { memo } from "react";
import { LayoutGroup, motion, useReducedMotion } from "framer-motion";

import { cn } from "../../lib/utils";

export interface PageTabItem {
  value: string;
  label: string;
  disabled?: boolean;
}

interface PageTabsProps {
  items: PageTabItem[];
  value: string;
  onValueChange: (value: string) => void;
  ariaLabel?: string;
  className?: string;
  indicatorId?: string;
}

const tabSpring = {
  type: "spring",
  stiffness: 320,
  damping: 28,
  mass: 0.75,
} as const;

export const PageTabs = memo(function PageTabs({
  items,
  value,
  onValueChange,
  ariaLabel = "Page sections",
  className,
  indicatorId = "page-tabs-indicator",
}: PageTabsProps) {
  const prefersReducedMotion = useReducedMotion();

  return (
    <div className={cn("overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden", className)}>
      <LayoutGroup id={indicatorId}>
        <div
          role="tablist"
          aria-label={ariaLabel}
          className="flex min-w-max items-center gap-2 px-3 py-3"
        >
          {items.map((item) => {
            const isActive = item.value === value;

            return (
              <motion.button
                key={item.value}
                type="button"
                role="tab"
                aria-selected={isActive}
                aria-current={isActive ? "page" : undefined}
                disabled={item.disabled}
                onClick={() => onValueChange(item.value)}
                whileHover={prefersReducedMotion || item.disabled ? undefined : { scale: 1.02 }}
                whileTap={prefersReducedMotion || item.disabled ? undefined : { scale: 0.985 }}
                transition={tabSpring}
                className={cn(
                  "relative inline-flex h-10 items-center justify-center whitespace-nowrap rounded-[1.1rem] border border-transparent bg-transparent px-3.5 text-sm font-medium tracking-tight text-left shadow-none transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  "hover:bg-background/45 hover:text-foreground dark:hover:bg-white/6",
                  isActive
                    ? "text-foreground"
                    : "text-muted-foreground hover:text-foreground",
                  item.disabled && "cursor-not-allowed opacity-50",
                )}
              >
                {isActive ? (
                  <motion.span
                    layoutId={indicatorId}
                    transition={tabSpring}
                    className="absolute inset-0 rounded-[1.1rem] border border-border/80 bg-card/88 shadow-[0_20px_40px_-28px_rgba(15,23,42,0.65)] backdrop-blur-sm dark:bg-zinc-950/70"
                  />
                ) : null}
                <span className="relative z-10">{item.label}</span>
              </motion.button>
            );
          })}
        </div>
      </LayoutGroup>
    </div>
  );
});
