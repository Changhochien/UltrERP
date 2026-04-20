import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { cn } from "../../lib/utils";

export interface BreadcrumbItem {
  label: ReactNode;
  href?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  separator?: ReactNode;
  className?: string;
}

function BreadcrumbTrail({
  items,
  separator,
  className,
}: {
  items: BreadcrumbItem[];
  separator: ReactNode;
  className?: string;
}) {
  return (
    <ol className={cn("flex min-w-0 items-center gap-2 text-xs font-medium text-muted-foreground", className)}>
      {items.map((item, index) => {
        const isCurrent = index === items.length - 1 || !item.href;

        return (
          <li key={`${index}-${typeof item.label === "string" ? item.label : "crumb"}`} className="flex min-w-0 items-center gap-2">
            {index > 0 ? (
              <span aria-hidden="true" className="shrink-0 text-muted-foreground/60">
                {separator}
              </span>
            ) : null}
            {isCurrent ? (
              <span aria-current="page" className="truncate text-foreground">
                {item.label}
              </span>
            ) : (
              <Link
                to={item.href}
                className="truncate transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              >
                {item.label}
              </Link>
            )}
          </li>
        );
      })}
    </ol>
  );
}

export function Breadcrumb({ items, separator = "/", className }: BreadcrumbProps) {
  if (items.length === 0) {
    return null;
  }

  const shouldCollapseOnMobile = items.length > 2;
  const collapsedItems = shouldCollapseOnMobile
    ? [{ label: "…" }, ...items.slice(-2)]
    : items;

  return (
    <nav aria-label="Breadcrumb" className={className}>
      {shouldCollapseOnMobile ? (
        <>
          <BreadcrumbTrail items={collapsedItems} separator={separator} className="sm:hidden" />
          <BreadcrumbTrail items={items} separator={separator} className="hidden sm:flex" />
        </>
      ) : (
        <BreadcrumbTrail items={items} separator={separator} />
      )}
    </nav>
  );
}