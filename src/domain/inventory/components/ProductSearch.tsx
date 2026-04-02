/** Product search with virtualized results list. */

import type { ReactElement } from "react";
import { List, type RowComponentProps } from "react-window";
import { useProductSearch } from "../hooks/useProductSearch";
import { useWarehouseContext } from "../context/WarehouseContext";
import type { ProductSearchResult } from "../types";

const ROW_HEIGHT = 48;
const LIST_HEIGHT = 480;

interface CustomRowProps {
  items: ProductSearchResult[];
}

function Row({
  index,
  style,
  items,
}: RowComponentProps<CustomRowProps>): ReactElement {
  const item = items[index];
  return (
    <div style={{ ...style, display: "flex", alignItems: "center", gap: 12 }}>
      <span style={{ width: 120, fontFamily: "monospace" }}>{item.code}</span>
      <span style={{ flex: 1 }}>{item.name}</span>
      <span style={{ width: 80 }}>{item.category ?? "—"}</span>
      <span style={{ width: 60, textAlign: "right" }}>
        {item.current_stock}
      </span>
    </div>
  );
}

export function ProductSearch() {
  const { results, loading, error, search } = useProductSearch();
  const { selectedWarehouse } = useWarehouseContext();

  return (
    <div>
      <h2>Product Search</h2>
      <input
        type="search"
        placeholder="Search by code or name (min 3 chars)…"
        onChange={(e) => search(e.target.value, selectedWarehouse?.id)}
        aria-label="Search products"
      />

      {loading && <p>Searching…</p>}
      {error && (
        <p className="error">
          {error}{" "}
          <button type="button" onClick={() => search("", selectedWarehouse?.id)}>
            Retry
          </button>
        </p>
      )}

      {!loading && !error && results.length === 0 && (
        <p>No results found.</p>
      )}

      {results.length > 0 && (
        <>
          <div
            style={{
              display: "flex",
              fontWeight: "bold",
              gap: 12,
              padding: "4px 0",
            }}
          >
            <span style={{ width: 120 }}>Code</span>
            <span style={{ flex: 1 }}>Name</span>
            <span style={{ width: 80 }}>Category</span>
            <span style={{ width: 60, textAlign: "right" }}>Stock</span>
          </div>
          <List<CustomRowProps>
            rowComponent={Row}
            rowCount={results.length}
            rowHeight={ROW_HEIGHT}
            rowProps={{ items: results }}
            style={{ height: LIST_HEIGHT }}
          />
        </>
      )}
    </div>
  );
}
