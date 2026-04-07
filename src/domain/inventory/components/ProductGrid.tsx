import { Package, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useProductSearch } from "../hooks/useProductSearch";
import { useWarehouseContext } from "../context/WarehouseContext";
import type { ProductSearchResult } from "../types";

type SortKey = "name" | "code" | "current_stock" | "category";
type SortDir = "asc" | "desc";
type StatusFilter = "all" | "active" | "inactive" | "low" | "critical";

interface ProductGridProps {
  onProductClick?: (productId: string) => void;
}

function getStockStatus(
  product: ProductSearchResult,
): "healthy" | "warning" | "critical" | "inactive" {
  if (product.status !== "active") return "inactive";
  if (product.current_stock === 0) return "critical";
  if (product.current_stock < 5) return "critical";
  if (product.current_stock < 20) return "warning";
  return "healthy";
}

function stockBarPercent(product: ProductSearchResult): number {
  return Math.min(100, (product.current_stock / 200) * 100);
}

export function ProductGrid({ onProductClick }: ProductGridProps) {
  const { selectedWarehouse } = useWarehouseContext();
  const { results, loading, error, search } = useProductSearch();

  const [searchInput, setSearchInput] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  // Load all on mount
  useEffect(() => {
    search("", selectedWarehouse?.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      search(searchInput, selectedWarehouse?.id);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput, search, selectedWarehouse]);

  const filtered = useMemo(() => {
    let data = [...results];

    if (statusFilter !== "all") {
      data = data.filter((p) => {
        const s = getStockStatus(p);
        if (statusFilter === "active") return s === "healthy";
        if (statusFilter === "inactive") return s === "inactive";
        if (statusFilter === "low") return s === "warning";
        if (statusFilter === "critical") return s === "critical";
        return true;
      });
    }

    data.sort((a, b) => {
      let va: string | number = a[sortKey] ?? "";
      let vb: string | number = b[sortKey] ?? "";
      if (typeof va === "string") va = va.toLowerCase();
      if (typeof vb === "string") vb = vb.toLowerCase();
      if (va < vb) return sortDir === "asc" ? -1 : 1;
      if (va > vb) return sortDir === "asc" ? 1 : -1;
      return 0;
    });

    return data;
  }, [results, statusFilter, sortKey, sortDir]);

  return (
    <div>
      {/* Grid Header */}
      <div className="product-grid-header">
        <div className="command-search" style={{ flex: 1, maxWidth: "100%" }}>
          <Search size={15} />
          <input
            type="search"
            placeholder="Search by code or name…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            aria-label="Search products"
          />
        </div>

        <select
          className="inv-select"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
          aria-label="Filter by status"
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="low">Low Stock</option>
          <option value="critical">Critical</option>
          <option value="inactive">Inactive</option>
        </select>

        <select
          className="inv-select"
          value={`${sortKey}-${sortDir}`}
          onChange={(e) => {
            const [key, dir] = e.target.value.split("-") as [SortKey, SortDir];
            setSortKey(key);
            setSortDir(dir);
          }}
          aria-label="Sort by"
        >
          <option value="name-asc">Name A→Z</option>
          <option value="name-desc">Name Z→A</option>
          <option value="code-asc">Code A→Z</option>
          <option value="code-desc">Code Z→A</option>
          <option value="current_stock-desc">Stock High→Low</option>
          <option value="current_stock-asc">Stock Low→High</option>
          <option value="category-asc">Category A→Z</option>
          <option value="category-desc">Category Z→A</option>
        </select>

        <span className="grid-count">
          {loading ? "—" : `${filtered.length} products`}
        </span>
      </div>

      {/* Grid */}
      <div className="product-grid" style={{ marginTop: 12 }}>
        {loading ? (
          Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="skeleton-card" style={{ height: 140 }} />
          ))
        ) : error ? (
          <div className="product-grid-empty">
            <Search size={40} />
            <p style={{ fontSize: 14, fontWeight: 600 }}>Failed to load products</p>
            <p style={{ fontSize: 12 }}>{error}</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="product-grid-empty">
            <Package size={40} />
            <p style={{ fontSize: 14, fontWeight: 600 }}>No products found</p>
            <p style={{ fontSize: 12 }}>
              {searchInput ? "Try a different search term" : "No products in the system"}
            </p>
          </div>
        ) : (
          filtered.map((product, index) => {
            const status = getStockStatus(product);
            const barPercent = stockBarPercent(product);

            return (
              <div
                key={product.id}
                className="product-card"
                style={{ animationDelay: `${Math.min(index * 25, 400)}ms` }}
                onClick={() => onProductClick?.(product.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onProductClick?.(product.id);
                  }
                }}
                aria-label={`${product.code} ${product.name}`}
              >
                <div className="product-card-header">
                  <span className="product-code">{product.code}</span>
                  <div className={`status-dot ${status}`} />
                </div>

                <div className="product-name">{product.name}</div>

                <div className="product-meta">
                  {product.category && (
                    <span className="category-tag">{product.category}</span>
                  )}
                </div>

                <div className="stock-info">
                  <span className={`stock-number ${status !== "healthy" ? status : ""}`}>
                    {product.current_stock}
                  </span>
                  <span className="stock-label">units</span>
                </div>

                <div className="stock-bar-wrap">
                  <div className="stock-bar">
                    <div
                      className={`stock-bar-fill ${status !== "healthy" ? status : "healthy"}`}
                      style={{ width: `${barPercent}%` }}
                    />
                  </div>
                </div>

                <div className="product-card-warehouse-hint">
                  <div className="warehouse-hint-row">
                    <span>Scope</span>
                    <span>{selectedWarehouse?.name ?? "All warehouses"}</span>
                  </div>
                  <div className="warehouse-hint-row">
                    <span>Status</span>
                    <span style={{ textTransform: "capitalize" }}>{status}</span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
