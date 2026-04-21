import { Plus, Search, ArrowRightLeft, ShoppingCart } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";

interface CommandBarProps {
  onAdjustStock?: () => void;
  onNewTransfer?: () => void;
  onNewOrder?: () => void;
  onSearch?: (query: string) => void;
  searchValue?: string;
  ariaLabel?: string;
  searchPlaceholder?: string;
  searchAriaLabel?: string;
  adjustStockLabel?: string;
  newTransferLabel?: string;
  newOrderLabel?: string;
}

export function CommandBar({
  onAdjustStock,
  onNewTransfer,
  onNewOrder,
  onSearch,
  searchValue = "",
  ariaLabel = "Inventory commands",
  searchPlaceholder = "Search products by code or name...",
  searchAriaLabel = "Search products",
  adjustStockLabel = "Adjust Stock",
  newTransferLabel = "New Transfer",
  newOrderLabel = "New Order",
}: CommandBarProps) {
  const actions = [
    onAdjustStock
      ? {
          key: "adjust-stock",
          label: adjustStockLabel,
          shortcut: "⌘A",
          icon: <Plus size={14} />,
          onClick: onAdjustStock,
        }
      : null,
    onNewTransfer
      ? {
          key: "new-transfer",
          label: newTransferLabel,
          shortcut: "⌘T",
          icon: <ArrowRightLeft size={14} />,
          onClick: onNewTransfer,
        }
      : null,
    onNewOrder
      ? {
          key: "new-order",
          label: newOrderLabel,
          shortcut: "⌘O",
          icon: <ShoppingCart size={14} />,
          onClick: onNewOrder,
        }
      : null,
  ].filter(Boolean) as Array<{
    key: string;
    label: string;
    shortcut: string;
    icon: ReactNode;
    onClick: () => void;
  }>;

  return (
    <section
      aria-label={ariaLabel}
      className="flex flex-col gap-3 rounded-2xl border border-border/80 bg-card/95 p-4 text-card-foreground shadow-[0_12px_40px_-28px_rgba(15,23,42,0.45)] lg:flex-row lg:items-center lg:justify-between"
    >
      <div className="relative flex-1">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          placeholder={searchPlaceholder}
          value={searchValue}
          onChange={(e) => onSearch?.(e.target.value)}
          aria-label={searchAriaLabel}
          className="pr-13 pl-9"
        />
        <span className="pointer-events-none absolute right-2 top-1/2 hidden -translate-y-1/2 rounded-md border border-border/70 bg-muted/70 px-2 py-0.5 text-[11px] font-medium text-muted-foreground sm:inline-flex">
          ⌘K
        </span>
      </div>

      {actions.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2">
          {actions.map((action) => (
            <Button
              key={action.key}
              type="button"
              variant="outline"
              size="sm"
              onClick={action.onClick}
            >
              {action.icon}
              {action.label}
              <span className="ml-1 hidden rounded-md border border-border/70 bg-muted/70 px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground md:inline-flex">
                {action.shortcut}
              </span>
            </Button>
          ))}
        </div>
      ) : null}
    </section>
  );
}
