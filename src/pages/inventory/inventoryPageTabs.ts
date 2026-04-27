import type { TFunction } from "i18next";

import type { PageTabItem } from "@/components/layout/PageTabs";
import {
  INVENTORY_BELOW_REORDER_REPORT_ROUTE,
  INVENTORY_CATEGORIES_ROUTE,
  INVENTORY_COUNT_SESSIONS_ROUTE,
  INVENTORY_REORDER_SUGGESTIONS_ROUTE,
  INVENTORY_ROUTE,
  INVENTORY_SUPPLIERS_ROUTE,
  INVENTORY_TRANSFERS_ROUTE,
  INVENTORY_UNITS_ROUTE,
  INVENTORY_VALUATION_ROUTE,
} from "@/lib/routes";

export type InventorySectionTabValue =
  | "overview"
  | "below-reorder"
  | "valuation"
  | "reorder-suggestions"
  | "count-sessions"
  | "transfers"
  | "units"
  | "categories"
  | "suppliers";

export function buildInventorySectionTabs(tRoutes: TFunction): PageTabItem[] {
  return [
    { value: "overview", label: tRoutes("inventory.label") },
    { value: "below-reorder", label: tRoutes("belowReorderReport.label") },
    { value: "valuation", label: tRoutes("inventoryValuation.label") },
    { value: "reorder-suggestions", label: tRoutes("reorderSuggestions.label") },
    { value: "count-sessions", label: tRoutes("inventoryCountSessions.label") },
    { value: "transfers", label: tRoutes("inventoryTransfers.label") },
    { value: "units", label: tRoutes("inventoryUnits.label") },
    { value: "categories", label: tRoutes("inventoryCategories.label") },
    { value: "suppliers", label: tRoutes("inventorySuppliers.label") },
  ];
}

export function getInventorySectionRoute(section: InventorySectionTabValue): string {
  switch (section) {
    case "overview":
      return INVENTORY_ROUTE;
    case "below-reorder":
      return INVENTORY_BELOW_REORDER_REPORT_ROUTE;
    case "valuation":
      return INVENTORY_VALUATION_ROUTE;
    case "reorder-suggestions":
      return INVENTORY_REORDER_SUGGESTIONS_ROUTE;
    case "count-sessions":
      return INVENTORY_COUNT_SESSIONS_ROUTE;
    case "transfers":
      return INVENTORY_TRANSFERS_ROUTE;
    case "units":
      return INVENTORY_UNITS_ROUTE;
    case "categories":
      return INVENTORY_CATEGORIES_ROUTE;
    case "suppliers":
      return INVENTORY_SUPPLIERS_ROUTE;
  }
}
