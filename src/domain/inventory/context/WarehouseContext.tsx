/** Warehouse context — persists selected warehouse across inventory screens. */

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";
import type { Warehouse } from "../types";

const STORAGE_KEY = "ultrerp:selected-warehouse";

function loadWarehouse(): Warehouse | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Warehouse) : null;
  } catch {
    return null;
  }
}

interface WarehouseContextValue {
  /** Currently selected warehouse (null = all warehouses / no filter). */
  selectedWarehouse: Warehouse | null;
  /** Set the active warehouse for the session. Pass null to clear. */
  setSelectedWarehouse: (warehouse: Warehouse | null) => void;
}

const WarehouseContext = createContext<WarehouseContextValue | null>(null);

export function WarehouseProvider({ children }: { children: ReactNode }) {
  const [selectedWarehouse, setSelected] = useState<Warehouse | null>(
    loadWarehouse,
  );

  const setSelectedWarehouse = useCallback(
    (warehouse: Warehouse | null) => {
      setSelected(warehouse);
      if (warehouse) {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(warehouse));
      } else {
        sessionStorage.removeItem(STORAGE_KEY);
      }
    },
    [],
  );

  return (
    <WarehouseContext.Provider
      value={{ selectedWarehouse, setSelectedWarehouse }}
    >
      {children}
    </WarehouseContext.Provider>
  );
}

export function useWarehouseContext(): WarehouseContextValue {
  const ctx = useContext(WarehouseContext);
  if (ctx === null) {
    throw new Error(
      "useWarehouseContext must be used within a WarehouseProvider",
    );
  }
  return ctx;
}
