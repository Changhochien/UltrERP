# Inventory Domain CQRS Extraction Plan

**Generated:** 2026-04-25  
**Source:** `backend/domains/inventory/services.py` (4801 lines, 64 public functions)  
**Target Pattern:** CQRS with commands/queries separation + domain helpers

---

## Overview

| Category | Count | Target Module |
|----------|-------|---------------|
| Commands | 31 | `commands/` |
| Queries | 31 | `queries/` |
| Domain Helpers | 2 public | `domain/_shared.py` |

---

## Commands (Write Operations)

| Function | Target File | Description |
|----------|-------------|-------------|
| `create_warehouse` | `commands/_warehouse.py` | Create new warehouse |
| `create_category` | `commands/_category.py` | Create category with translations |
| `update_category` | `commands/_category.py` | Update category data |
| `set_category_status` | `commands/_category.py` | Activate/deactivate category |
| `seed_default_units` | `commands/_unit.py` | Bootstrap default UoM list |
| `create_unit` | `commands/_unit.py` | Create unit of measure |
| `update_unit` | `commands/_unit.py` | Update unit of measure |
| `set_unit_status` | `commands/_unit.py` | Activate/deactivate unit |
| `create_product` | `commands/_product.py` | Create product record |
| `update_product` | `commands/_product.py` | Update product data |
| `set_product_status` | `commands/_product.py` | Activate/deactivate product |
| `transfer_stock` | `commands/_stock.py` | Execute stock transfer between warehouses |
| `create_stock_adjustment` | `commands/_stock.py` | Record stock adjustment |
| `update_stock_settings` | `commands/_stock.py` | Update reorder points, safety stock |
| `create_physical_count_session` | `commands/_physical_count.py` | Start inventory count session |
| `update_physical_count_line` | `commands/_physical_count.py` | Update count line quantities |
| `submit_physical_count_session` | `commands/_physical_count.py` | Submit session for approval |
| `approve_physical_count_session` | `commands/_physical_count.py` | Approve and apply adjustments |
| `acknowledge_alert` | `commands/_alerts.py` | Mark alert as acknowledged |
| `snooze_alert` | `commands/_alerts.py` | Snooze alert temporarily |
| `dismiss_alert` | `commands/_alerts.py` | Dismiss alert permanently |
| `create_reorder_suggestion_orders` | `commands/_alerts.py` | Generate purchase orders from suggestions |
| `create_supplier` | `commands/_supplier.py` | Create supplier record |
| `update_supplier` | `commands/_supplier.py` | Update supplier data |
| `set_supplier_status` | `commands/_supplier.py` | Activate/deactivate supplier |
| `create_supplier_order` | `commands/_supplier.py` | Create purchase order |
| `receive_supplier_order` | `commands/_supplier.py` | Record goods receipt |
| `update_supplier_order_status` | `commands/_supplier.py` | Update PO status |
| `create_product_supplier` | `commands/_product_supplier.py` | Link product to supplier |
| `update_product_supplier` | `commands/_product_supplier.py` | Update product-supplier link |
| `delete_product_supplier` | `commands/_product_supplier.py` | Remove product-supplier link |

---

## Queries (Read Operations)

| Function | Target File | Description |
|----------|-------------|-------------|
| `list_warehouses` | `queries/_warehouse.py` | List all warehouses |
| `get_warehouse` | `queries/_warehouse.py` | Get single warehouse by ID |
| `list_categories` | `queries/_category.py` | List categories with pagination |
| `get_category` | `queries/_category.py` | Get category by ID |
| `list_units` | `queries/_unit.py` | List units of measure |
| `get_unit` | `queries/_unit.py` | Get unit by ID |
| `list_transfers` | `queries/_stock.py` | List stock transfers |
| `get_transfer` | `queries/_stock.py` | Get transfer details |
| `list_physical_count_sessions` | `queries/_physical_count.py` | List count sessions |
| `get_physical_count_session` | `queries/_physical_count.py` | Get session with lines |
| `list_reorder_alerts` | `queries/_alerts.py` | List active reorder alerts |
| `list_reorder_suggestions` | `queries/_alerts.py` | List reorder recommendations |
| `list_below_reorder_products` | `queries/_alerts.py` | Products below reorder point |
| `get_inventory_valuation` | `queries/_stock.py` | Stock valuation report |
| `get_inventory_stocks` | `queries/_stock.py` | Current stock levels |
| `get_product_detail` | `queries/_product.py` | Product with relations |
| `search_products` | `queries/_product.py` | Full-text product search |
| `list_suppliers` | `queries/_supplier.py` | List suppliers |
| `get_supplier` | `queries/_supplier.py` | Get supplier details |
| `get_supplier_order` | `queries/_supplier.py` | Get PO details |
| `list_supplier_orders` | `queries/_supplier.py` | List purchase orders |
| `get_stock_history` | `queries/_stock.py` | Stock movement history |
| `get_stock_history_series` | `queries/_stock.py` | Time-series stock data |
| `get_monthly_demand` | `queries/_analytics.py` | Monthly demand aggregation |
| `get_monthly_demand_series` | `queries/_analytics.py` | Demand time series |
| `get_planning_support` | `queries/_analytics.py` | Planning support data |
| `get_sales_history` | `queries/_analytics.py` | Historical sales data |
| `get_top_customer` | `queries/_analytics.py` | Top customer by volume |
| `list_product_suppliers` | `queries/_product_supplier.py` | List product-supplier links |
| `get_product_supplier` | `queries/_product_supplier.py` | Get link details |
| `get_product_audit_log` | `queries/_product.py` | Product change history |

---

## Domain Helpers (Pure Functions)

| Function | Current Location | Target Location | Status |
|----------|-----------------|----------------|--------|
| `resolve_category_locale` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `serialize_category` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `quantize_quantity` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `quantize_index` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `quantize_valuation_amount` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `normalize_standard_cost` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `normalize_unit_code` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `normalize_unit_name` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `normalize_optional_product_text` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `normalize_category_name` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `normalize_category_locale` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `normalize_category_translations` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `category_translation_map` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `localized_category_name` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `iter_month_starts` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `format_month` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `DEFAULT_UNIT_OF_MEASURE_SEEDS` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `SUPPORTED_CATEGORY_LOCALES` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `DEFAULT_CATEGORY_LOCALE` | `services.py` | `domain/_shared.py` | ✅ Already extracted |
| `ZH_HANT_LOCALE` | `services.py` | `domain/_shared.py` | ✅ Already extracted |

### Constants (remain in `domain/_shared.py`)

```python
# Quantization
_PLANNING_QUANTITY_QUANT = Decimal("0.001")
_PLANNING_INDEX_QUANT = Decimal("0.001")
_STANDARD_COST_QUANT = Decimal("0.0001")
_VALUATION_AMOUNT_QUANT = Decimal("0.0001")
_ZERO_QUANTITY = Decimal("0.000")
```

---

## Module Structure (Post-Extraction)

```
backend/domains/inventory/
├── __init__.py              # Re-export all public APIs (backward compat)
├── services.py              # Legacy facade (calls into commands/queries)
├── commands/
│   ├── __init__.py          # Re-exports all commands
│   ├── _warehouse.py        # Warehouse write operations
│   ├── _category.py         # Category write operations
│   ├── _unit.py             # Unit of measure write operations
│   ├── _product.py          # Product write operations
│   ├── _stock.py            # Stock transfer/adjustment operations
│   ├── _physical_count.py   # Physical count operations
│   ├── _alerts.py           # Reorder alert operations
│   ├── _supplier.py         # Supplier + PO operations
│   └── _product_supplier.py # Product-supplier link operations
├── queries/
│   ├── __init__.py          # Re-exports all queries
│   ├── _warehouse.py        # Warehouse read operations
│   ├── _category.py         # Category read operations
│   ├── _unit.py             # Unit of measure read operations
│   ├── _product.py          # Product read operations
│   ├── _stock.py            # Stock read operations
│   ├── _physical_count.py   # Physical count read operations
│   ├── _alerts.py           # Reorder alert read operations
│   ├── _supplier.py         # Supplier + PO read operations
│   ├── _product_supplier.py # Product-supplier link read operations
│   └── _analytics.py        # Analytics/read-only aggregations
└── domain/
    ├── __init__.py          # Public domain API
    └── _shared.py           # Pure helpers, constants, types
```

---

## Private Helpers (Remain Internal)

These private functions are tightly coupled to their domain modules and should NOT be extracted:

| Function | Reason |
|----------|--------|
| `_find_unit_by_code` | Used only by unit commands/queries |
| `_find_product_by_code` | Used only by product commands |
| `_find_category_by_name` | Used only by category commands |
| `_find_category_by_id` | Used only by category operations |
| `_resolve_product_category` | Used only by product commands |
| `_physical_count_status_value` | Internal type coercion |
| `_serialize_physical_count_line` | Internal serialization |
| `_serialize_physical_count_session` | Internal serialization |
| `_add_physical_count_audit` | Internal audit helper |
| `_get_physical_count_session_record` | Internal fetch helper |
| `_compute_severity` | Internal calculation |
| `_release_expired_snooze` | Internal alert logic |
| `_check_reorder_alert` | Internal alert check |
| `_load_reorder_suggestion_source` | Internal query builder |
| `_int_field` | Internal row parsing |
| `_serialize_reorder_suggestion_row` | Internal serialization |
| `_batch_get_product_suppliers` | Internal batch query |
| `_is_missing_product_supplier_table` | Migration check |
| `_product_supplier_table_exists` | Migration check |
| `_load_product_supplier_explicit_row` | Internal query |
| `_serialize_below_reorder_report_row` | Internal serialization |
| `_resolve_inventory_valuation_cost` | Internal calculation |
| `_serialize_inventory_valuation_row` | Internal serialization |
| `_serialize_order` | Internal PO serialization |
| `_validate_product_supplier_scope` | Internal validation |
| `_serialize_product_supplier_association` | Internal serialization |

---

## Migration Strategy

### Phase 1: Domain Helpers (COMPLETE)
- [x] Extract pure functions to `domain/_shared.py`
- [x] Update imports in `services.py`

### Phase 2: Commands (commands/_*.py)
- [x] Create `commands/_warehouse.py` — extract `create_warehouse`
- [x] Create `commands/_category.py` — extract CRUD operations
- [x] Create `commands/_unit.py` — extract UoM operations
- [ ] Create `commands/_product.py` — extract product operations
- [ ] Create `commands/_stock.py` — extract stock operations
- [ ] Create `commands/_physical_count.py` — extract count operations
- [ ] Create `commands/_alerts.py` — extract alert operations
- [ ] Create `commands/_supplier.py` — extract supplier/PO operations
- [ ] Create `commands/_product_supplier.py` — extract link operations
- [ ] Update `commands/__init__.py` to re-export

### Phase 3: Queries (queries/_*.py)
- [x] Create `queries/_warehouse.py` — extract warehouse queries
- [x] Create `queries/_category.py` — extract category queries
- [x] Create `queries/_unit.py` — extract UoM queries
- [ ] Create `queries/_product.py` — extract product queries + audit log
- [ ] Create `queries/_stock.py` — extract stock queries
- [ ] Create `queries/_physical_count.py` — extract count queries
- [ ] Create `queries/_alerts.py` — extract alert queries
- [ ] Create `queries/_supplier.py` — extract supplier/PO queries
- [ ] Create `queries/_product_supplier.py` — extract link queries
- [ ] Create `queries/_analytics.py` — extract analytics queries
- [ ] Update `queries/__init__.py` to re-export

### Phase 4: Facade Cleanup (services.py)
- [ ] Replace implementations with imports from commands/queries
- [ ] Keep only facade + private helpers
- [ ] Add deprecation warnings

### Phase 5: Backward Compatibility
- [ ] Update `__init__.py` to re-export from commands/queries
- [ ] Update all internal callers to use new modules
- [ ] Add deprecation notices to services.py exports

---

## Exceptions to Keep in services.py

These exception classes are domain-specific and should remain accessible:

```python
class InsufficientStockError(Exception)
class TransferValidationError(Exception)
class PhysicalCountNotFoundError(Exception)
class PhysicalCountConflictError(Exception)
class PhysicalCountStateError(Exception)
```

Re-export from `services.py` for backward compatibility.
