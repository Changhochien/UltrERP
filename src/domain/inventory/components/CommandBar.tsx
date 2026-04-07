import { Plus, Search, ArrowRightLeft, ShoppingCart } from "lucide-react";

interface CommandBarProps {
  onAdjustStock?: () => void;
  onNewTransfer?: () => void;
  onNewOrder?: () => void;
  onSearch?: (query: string) => void;
  searchValue?: string;
}

export function CommandBar({
  onAdjustStock,
  onNewTransfer,
  onNewOrder,
  onSearch,
  searchValue = "",
}: CommandBarProps) {
  return (
    <div className="command-bar">
      <div className="command-search">
        <Search size={15} />
        <input
          type="search"
          placeholder="Search products by code or name…"
          value={searchValue}
          onChange={(e) => onSearch?.(e.target.value)}
          aria-label="Search products"
        />
        <span className="command-shortcut">⌘K</span>
      </div>

      <div className="command-actions">
        <button
          type="button"
          className="drawer-action-btn"
          onClick={onAdjustStock}
        >
          <Plus size={14} />
          Adjust Stock
          <span className="command-shortcut">⌘A</span>
        </button>

        <button
          type="button"
          className="drawer-action-btn"
          onClick={onNewTransfer}
        >
          <ArrowRightLeft size={14} />
          New Transfer
          <span className="command-shortcut">⌘T</span>
        </button>

        <button
          type="button"
          className="drawer-action-btn"
          onClick={onNewOrder}
        >
          <ShoppingCart size={14} />
          New Order
          <span className="command-shortcut">⌘O</span>
        </button>
      </div>
    </div>
  );
}
