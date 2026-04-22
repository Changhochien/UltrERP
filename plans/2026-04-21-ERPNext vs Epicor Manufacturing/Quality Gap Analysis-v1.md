# UltrERP Manufacturing, Inventory & Quality Gap Analysis

**Date:** 2026-04-21  
**Reference:** ERPnext v14/v15 source at `/reference/erpnext-develop/`  
**Compared Against:** Epicor Epic 24 (Purchasing), Epic 27 (Manufacturing), Epic 29 (Quality Control), Epic 32 (Subcontracting)

---

## Executive Summary

UltrERP currently has **zero manufacturing, quality, or advanced inventory capabilities**. The existing inventory domain covers basic CRUD operations and stock transfers, but lacks the structural foundations for BOM, Work Orders, Quality Inspection, Serial/Batch tracking, Landed Cost, Putaway Rules, and Subcontracting workflows.

ERPNext provides comprehensive manufacturing and quality modules with deep integration across these domains. The gap is **100%** for Epic 27/29/32 features and **~85%** for Epic 4/24 inventory features.

---

## 1. Manufacturing (Epic 27 Coverage)

### 1.1 BOM Types

| ERPNext Feature | Reference | Epic 27 Alignment | Status in UltrERP |
|-----------------|-----------|-------------------|-------------------|
| **BOM - Manufacture** | `erpnext/manufacturing/doctype/bom/bom.json` | Product recipe definition | **MISSING** |
| **BOM - Subcontracting** | `erpnext/manufacturing/doctype/bom/bom.json` (with `is_subcontracted_item` on Item) | Outsourcing recipe | **MISSING** |
| **Phantom BOM** | `bom.json:645` — `is_phantom_bom` field | Kit/assembly items | **MISSING** |
| **Multi-level BOM** | `bom.json:175` — `use_multi_level_bom` on WO | Nested assemblies | **MISSING** |
| **BOM Operations** | `erpnext/manufacturing/doctype/bom_operation/bom_operation.json` | Routing operations | **MISSING** |
| **BOM Costing** | `bom.json:305-365` — raw_material_cost, operating_cost, total_cost | Cost rollup | **MISSING** |
| **Process Loss** | `bom.json:532-548` — process_loss_percentage, process_loss_qty | Yield tracking | **MISSING** |
| **Quality Inspection on BOM** | `bom.json:186-210` — `inspection_required`, `quality_inspection_template` | QC gating | **MISSING** |
| **BOM Creator** | `erpnext/manufacturing/doctype/bom_creator/bom_creator.json` | BOM wizard | **MISSING** |
| **BOM Update Tool** | `erpnext/manufacturing/doctype/bom_update_tool/bom_update_tool.json` | Multi-level cost updates | **MISSING** |

### 1.2 Work Order Lifecycle

| ERPNext Feature | Reference | Epic 27 Alignment | Status in UltrERP |
|-----------------|-----------|-------------------|-------------------|
| **Work Order Creation** | `erpnext/manufacturing/doctype/work_order/work_order.json` | Production order | **MISSING** |
| **Status Machine** | `work_order.json:114-122` — Draft→Submitted→Not Started→In Process→Completed | State transitions | **MISSING** |
| **Material Transfer for Manufacture** | Stock Entry purpose type | Material staging | **MISSING** |
| **Manufacture Entry** | Stock Entry purpose type | FG production | **MISSING** |
| **Skip Material Transfer** | `work_order.json:184` — `skip_transfer` | Backflush mode | **MISSING** |
| **WIP Warehouse** | `work_order.json:266-270` — `wip_warehouse` | Work-in-progress staging | **MISSING** |
| **Scrap Warehouse** | `work_order.json:286-289` — `scrap_warehouse` | Scrap handling | **MISSING** |
| **Material Request Link** | `work_order.json:439-451` — `material_request`, `material_request_item` | MRP integration | **MISSING** |
| **Sales Order Link** | `work_order.json:236-241` — `sales_order` | Make-to-order | **MISSING** |
| **Production Plan Link** | `work_order.json:460-468` — `production_plan`, `production_plan_item` | Planning integration | **MISSING** |
| **Serial/Batch on FG** | `work_order.json:528-559` — `has_serial_no`, `has_batch_no`, `batch_size` | Serialized production | **MISSING** |
| **Operation Cost Tracking** | `work_order.json:374-406` — planned_operating_cost, actual_operating_cost | Manufacturing costing | **MISSING** |
| **Disassemble** | Stock Entry purpose "Disassemble" | Reverse production | **MISSING** |

### 1.3 Job Cards

| ERPNext Feature | Reference | Epic 27 Alignment | Status in UltrERP |
|-----------------|-----------|-------------------|-------------------|
| **Job Card Creation** | `erpnext/manufacturing/doctype/job_card/job_card.json` | Operation execution | **MISSING** |
| **Employee Time Logs** | `job_card.json:169-172` — `time_logs` table | Labor tracking | **MISSING** |
| **Scheduled Time** | `job_card.json:469-473` — `scheduled_time_logs` | Operation scheduling | **MISSING** |
| **Workstation Assignment** | `job_card.json:114-128` — `workstation`, `workstation_type` | Resource planning | **MISSING** |
| **Operation Status** | `job_card.json:257-262` — Open/WIP/Material Transferred/On Hold/Completed | Status tracking | **MISSING** |
| **Sub-Operations** | `job_card.json:335-338` — `sub_operations` table | Nested operations | **MISSING** |
| **Corrective Job Card** | `job_card.json:349-385` — `is_corrective_job_card`, `for_job_card` | Rework tracking | **MISSING** |
| **Semi-Finished Goods** | `job_card.json:497-510` — `finished_good`, `semi_fg_bom`, `target_warehouse` | Multi-stage production | **MISSING** |
| **Quality Inspection on Job Card** | `job_card.json:327-331, 410-414` — QI template and reference | Operation QC | **MISSING** |
| **Barcode Scanning** | `job_card.json:300-303` — `barcode` field | Shop floor data entry | **MISSING** |

### 1.4 Production Plan

| ERPNext Feature | Reference | Epic 27 Alignment | Status in UltrERP |
|-----------------|-----------|-------------------|-------------------|
| **Production Plan** | `erpnext/manufacturing/doctype/production_plan/production_plan.json` | MPS/MRP aggregation | **MISSING** |
| **Get from Sales Order** | `production_plan.json:85-174` — `get_sales_orders`, `sales_orders` table | Demand-driven planning | **MISSING** |
| **Get from Material Request** | `production_plan.json:176-194` — `get_material_request` | MRP integration | **MISSING** |
| **Sub-Assembly Planning** | `production_plan.json:361-429` — `sub_assembly_items`, `sub_assembly_warehouse` | Multi-level planning | **MISSING** |
| **Raw Material Planning** | `production_plan.json:216-266` — `mr_items`, `consider_minimum_order_qty` | Component sourcing | **MISSING** |
| **Combine Items** | `production_plan.json:344-348` — `combine_items` | Consolidation | **MISSING** |
| **Reserve Stock** | `production_plan.json:438-440` — `reserve_stock` | Stock reservation | **MISSING** |
| **Auto Create Work Orders** | Production Plan → Work Orders | Batch WO creation | **MISSING** |

### 1.5 Routing/Operations

| ERPNext Feature | Reference | Epic 27 Alignment | Status in UltrERP |
|-----------------|-----------|-------------------|-------------------|
| **Routing** | `erpnext/manufacturing/doctype/routing/routing.json` | Operation sequence master | **MISSING** |
| **Operation Master** | `erpnext/setup/doctype/operation/operation.json` | Work center operations | **MISSING** |
| **Workstation** | `erpnext/setup/doctype/workstation/workstation.json` | Machine/line definition | **MISSING** |
| **Workstation Working Hours** | `erpnext/manufacturing/doctype/workstation_working_hour/workstation_working_hour.json` | Capacity calendar | **MISSING** |
| **Operation Costing** | BOM Operation `hour_rate`, `time_in_mins`, `operating_cost` | Labor/machine costing | **MISSING** |
| **Workstation Type** | `erpnext/setup/doctype/workstation_type/workstation_type.json` | Resource grouping | **MISSING** |
| **Downtime Entry** | `erpnext/manufacturing/doctype/downtime_entry/downtime_entry.json` | OEE tracking | **MISSING** |
| **Plant Floor** | `erpnext/manufacturing/doctype/plant_floor/plant_floor.json` | Visual scheduling | **MISSING** |

### 1.6 Job Worker Subcontracting

| ERPNext Feature | Reference | Epic 32 Alignment | Status in UltrERP |
|-----------------|-----------|-------------------|-------------------|
| **Subcontracting Order** | `erpnext/subcontracting/doctype/subcontracting_order/subcontracting_order.json` | Job work orders | **MISSING** |
| **Service Items** | `subcontracting_order.json:306-317` — `service_items` | Processing charges | **MISSING** |
| **Supplied Items** | `subcontracting_order.json:319-342` — `supplied_items` | Material transfer tracking | **MISSING** |
| **Reserve Stock** | `subcontracting_order.json:479-483` — `reserve_stock` | Material reservation | **MISSING** |
| **Additional Costs** | `subcontracting_order.json:343-361` — `additional_costs`, `distribute_additional_costs_based_on` | Cost allocation | **MISSING** |
| **Subcontracting Receipt** | `erpnext/subcontracting/doctype/subcontracting_receipt/subcontracting_receipt.json` | FG return from subcontractor | **MISSING** |
| **Consumed Items Tracking** | `subcontracting_receipt.json:315-321` — `supplied_items` | Material consumption at subcontractor | **MISSING** |
| **Rejected Warehouse** | `subcontracting_receipt.json:257-266` — `rejected_warehouse` | Defective goods handling | **MISSING** |
| **Is Subcontracted on BOM Operation** | `bom_operation.json:271-274` — `is_subcontracted` | Per-operation outsourcing | **MISSING** |

### 1.7 Epic 27 vs ERPNext Summary

| Epic 27 Capability | ERPNext Coverage | Gap Severity |
|--------------------|------------------|--------------|
| Product Configurator | BOM + Item Variants | Partial |
| Estimating | BOM Costing | Complete |
| Production Planning | Production Plan | Complete |
| Shop Floor Control | Job Card + Work Order | Complete |
| Engineering | BOM + Routing | Complete |
| Configured Products | Item Variants + BOM | Partial |
| Co/By-Products | BOM Scrap Warehouse | Partial |
| Production Metrics | Dashboard + Reports | Complete |
| Quality Management | BOM + QI Integration | Complete |

**What's in ERPNext vs Epic 27:**
- ERPNext has **complete** Epic 27 production planning coverage (Production Plan, Work Orders, Job Cards, Routing)
- ERPNext has **superior** BOM flexibility (multi-level, phantom, subcontracting, process loss)
- ERPNext **lacks** advanced finite capacity scheduling (only basic scheduling)
- ERPNext **lacks** native capacity planning reports (requires custom)

---

## 2. Quality Management (Epic 29 Coverage)

### 2.1 Quality Inspection Templates

| ERPNext Feature | Reference | Epic 29 Alignment | Status in UltrERP |
|-----------------|-----------|-------------------|-------------------|
| **Quality Inspection Template** | `erpnext/stock/doctype/quality_inspection_template/quality_inspection_template.json` | Inspection checklist master | **MISSING** |
| **Inspection Parameters** | `erpnext/stock/doctype/quality_inspection_parameter/quality_inspection_parameter.json` | Measurement definitions | **MISSING** |
| **Acceptance Criteria** | Template → Readings with min/max | Pass/fail rules | **MISSING** |
| **Numeric/Non-Numeric Readings** | QI Reading field types | Various measurement types | **MISSING** |
| **Template Linking to Item** | `item.json:764-768` — `quality_inspection_template` on Item | Auto-assign template | **MISSING** |
| **Template Linking to BOM** | `bom.json:186-210` — QI template on BOM | Process inspection | **MISSING** |

### 2.2 Quality Procedure

| ERPNext Feature | Reference | Epic 29 Alignment | Status in UltrERP |
|-----------------|-----------|-------------------|-------------------|
| **Quality Procedure (Tree)** | `erpnext/quality_management/doctype/quality_procedure/quality_procedure.json` | SOP hierarchy | **MISSING** |
| **Process Steps** | `quality_procedure.json:64-68` — `processes` table | Procedure steps | **MISSING** |
| **Process Owner** | `quality_procedure.json:77-94` — `process_owner`, `process_owner_full_name` | Responsibility assignment | **MISSING** |
| **ISO/Procedure Linking** | Non-Conformance links to Procedure | Traceability | **MISSING** |
| **Quality Feedback Template** | `erpnext/quality_management/doctype/quality_feedback_template/quality_feedback_template.json` | Customer satisfaction | **MISSING** |

### 2.3 Quality Inspection Recording

| ERPNext Feature | Reference | Epic 29 Alignment | Status in UltrERP |
|-----------------|-----------|-------------------|-------------------|
| **Quality Inspection** | `erpnext/stock/doctype/quality_inspection/quality_inspection.json` | Inspection recording | **MISSING** |
| **Inspection Types** | `quality_inspection.json:67-75` — Incoming/In Process/Outgoing | Inspection contexts | **MISSING** |
| **Reference Documents** | `quality_inspection.json:78-94` — PR/DN/SE/Job Card | Source linking | **MISSING** |
| **Sample Size** | `quality_inspection.json:130-136` — `sample_size` | Sampling plan | **MISSING** |
| **Readings Table** | `quality_inspection.json:225-230` — `readings` | Actual measurements | **MISSING** |
| **Status: Accepted/Rejected** | `quality_inspection.json:233-238` | QC decision | **MISSING** |
| **BOM No Link** | `quality_inspection.json:182-187` — `bom_no` | Process inspection link | **MISSING** |
| **Serial/Batch Link** | `quality_inspection.json:114-128` — `item_serial_no`, `batch_no` | Traceability | **MISSING** |
| **Inspected By / Verified By** | `quality_inspection.json:165-180` | Personnel assignment | **MISSING** |
| **Manual Inspection** | `quality_inspection.json:242-244` — `manual_inspection` | Override capability | **MISSING** |
| **Auto-trigger from PR/DN** | Stock transaction workflow | Process integration | **MISSING** |

### 2.4 Non-Conformance Report (NCR)

| ERPNext Feature | Reference | Epic 29 Alignment | Status in UltrERP |
|-----------------|-----------|-------------------|-------------------|
| **Non Conformance** | `erpnext/quality_management/doctype/non_conformance/non_conformance.json` | Defect recording | **MISSING** |
| **Subject** | `non_conformance.json:21-27` — `subject` | Issue description | **MISSING** |
| **Procedure Link** | `non_conformance.json:28-34` — `procedure` | Root cause procedure | **MISSING** |
| **Process Owner** | `non_conformance.json:54-58` — `process_owner` | Responsibility | **MISSING** |
| **Details** | `non_conformance.json:49-52` — `details` | Issue documentation | **MISSING** |
| **Corrective Action** | `non_conformance.json:72-74` — `corrective_action` | Fix documentation | **MISSING** |
| **Preventive Action** | `non_conformance.json:76-79` — `preventive_action` | Future prevention | **MISSING** |
| **Status: Open/Resolved/Cancelled** | `non_conformance.json:37-42` | Resolution tracking | **MISSING** |

### 2.5 Corrective Action (CAP)

| ERPNext Feature | Reference | Epic 29 Alignment | Status in UltrERP |
|-----------------|-----------|-------------------|-------------------|
| **Quality Action** | `erpnext/quality_management/doctype/quality_action/quality_action.json` | CAPA management | **MISSING** |
| **Corrective/Preventive** | `quality_action.json:54-61` — `corrective_preventive` | CAPA classification | **MISSING** |
| **Resolutions Table** | `quality_action.json:72-77` — `resolutions` | Action items | **MISSING** |
| **Review Link** | `quality_action.json:78-84` — `review` | Management review | **MISSING** |
| **Goal Link** | `quality_action.json:23-28` — `goal` | Objective linkage | **MISSING** |
| **Procedure Link** | `quality_action.json:39-42` — `procedure` | SOP reference | **MISSING** |
| **Status: Open/Completed** | `quality_action.json:45-52` | Closure tracking | **MISSING** |

### 2.6 Quality Goals & Reviews

| ERPNext Feature | Reference | Epic 29 Alignment | Status in UltrERP |
|-----------------|-----------|-------------------|-------------------|
| **Quality Goal** | `erpnext/quality_management/doctype/quality_goal/quality_goal.json` | KPI definition | **MISSING** |
| **Objectives Table** | `quality_goal.json:57-62` — `objectives` | Metric tracking | **MISSING** |
| **Monitoring Frequency** | `quality_goal.json:20-26` — Daily/Weekly/Monthly/Quarterly | Review scheduling | **MISSING** |
| **Quality Review** | `erpnext/quality_management/doctype/quality_review/quality_review.json` | Management review | **MISSING** |
| **Quality Meeting** | `erpnext/quality_management/doctype/quality_meeting/quality_meeting.json` | Review meetings | **MISSING** |
| **Meeting Agenda** | `erpnext/quality_management/doctype/quality_meeting_agenda/quality_meeting_agenda.json` | Meeting preparation | **MISSING** |
| **Meeting Minutes** | `erpnext/quality_management/doctype/quality_meeting_minutes/quality_meeting_minutes.json` | Documentation | **MISSING** |

### 2.7 Epic 29 vs ERPNext Summary

| Epic 29 Capability | ERPNext Coverage | Gap Severity |
|--------------------|------------------|--------------|
| Inspection Plans | Quality Inspection Template | Complete |
| First Article Inspection | QI with BOM link | Complete |
| In-Process Inspection | Job Card QI | Complete |
| Final Inspection | Delivery Note QI | Complete |
| Non-Conformance Tracking | Non Conformance + Quality Action | Complete |
| Corrective/Preventive Action | Quality Action | Complete |
| Supplier Quality Management | QI on Purchase Receipt | Complete |
| Quality Audits | Quality Meeting + Review | Partial |
| Statistical Process Control | Not native | Missing |
| Gauge R&R | Not native | Missing |

---

## 3. Stock/Inventory (Epic 4, 29 Coverage)

### 3.1 Warehouse Management

| ERPNext Feature | Reference | Epic Coverage | Status in UltrERP |
|-----------------|-----------|---------------|-------------------|
| **Warehouse Tree** | `erpnext/stock/doctype/warehouse/warehouse.json` | Epic 4 | **Partially Present** |
| **Warehouse Type** | `warehouse.json` — `warehouse_type` field | Classification | **MISSING** |
| **Default for Rejected** | `warehouse.json` — `is_rejected_warehouse` | QC workflow | **MISSING** |
| **In-Transit Default** | Warehouse settings | Shipment staging | **MISSING** |
| **Warehouse Capacity** | Putaway Rule capacity | Storage limits | **Partially Present** |

### 3.2 Stock Reconciliation

| ERPNext Feature | Reference | Epic Coverage | Status in UltrERP |
|-----------------|-----------|---------------|-------------------|
| **Stock Reconciliation** | `erpnext/stock/doctype/stock_reconciliation/stock_reconciliation.json` | Physical count | **MISSING** |
| **Opening Stock Purpose** | `stock_reconciliation.json:55-59` — Opening Stock | Initial balances | **MISSING** |
| **Scan Mode** | `stock_reconciliation.json:163-166` — `scan_mode` | Barcode counting | **MISSING** |
| **Barcode Scanning** | `stock_reconciliation.json:156-159` — `scan_barcode` | Quick entry | **MISSING** |
| **Difference Account** | `stock_reconciliation.json:107-113` — `expense_account` | GL integration | **MISSING** |
| **Cost Center** | `stock_reconciliation.json:115-119` | Accounting dimensions | **MISSING** |

### 3.3 Stock Entry Types

| ERPNext Feature | Reference | Epic Coverage | Status in UltrERP |
|-----------------|-----------|---------------|-------------------|
| **Material Receipt** | Stock Entry purpose | Epic 4 | **Partially Present** |
| **Material Issue** | Stock Entry purpose | Epic 4 | **Partially Present** |
| **Material Transfer** | Stock Entry purpose | Epic 4 | **Partially Present** |
| **Material Transfer for Manufacture** | Stock Entry purpose + Pick List | Epic 27 | **MISSING** |
| **Manufacture** | Stock Entry purpose | Epic 27 | **MISSING** |
| **Repack** | Stock Entry purpose | Epic 4 | **MISSING** |
| **Send to Subcontractor** | Stock Entry purpose | Epic 32 | **MISSING** |
| **Disassemble** | Stock Entry purpose | Epic 27 | **MISSING** |
| **Receive from Customer** | Stock Entry purpose | Epic 4 | **MISSING** |
| **Subcontracting Delivery** | Stock Entry purpose | Epic 32 | **MISSING** |
| **Subcontracting Return** | Stock Entry purpose | Epic 32 | **MISSING** |
| **Process Loss** | `stock_entry.json:676-694` — `process_loss_percentage`, `process_loss_qty` | Epic 27 | **MISSING** |
| **Scan Barcode** | `stock_entry.json:375-379` — `scan_barcode` | Shop floor | **MISSING** |
| **Additional Costs** | `stock_entry.json:438-450` — `additional_costs` | Epic 4 | **MISSING** |

### 3.4 Pick List

| ERPNext Feature | Reference | Epic Coverage | Status in UltrERP |
|-----------------|-----------|---------------|-------------------|
| **Pick List** | `erpnext/stock/doctype/pick_list/pick_list.json` | Epic 4/27 | **MISSING** |
| **Purpose: Delivery** | `pick_list.json:109-113` | Order fulfillment | **MISSING** |
| **Purpose: Material Transfer for Manufacture** | `pick_list.json:109-113` | Epic 27 | **MISSING** |
| **Purpose: Material Transfer** | `pick_list.json:109-113` | Internal moves | **MISSING** |
| **Scan Mode** | `pick_list.json:167-169` — `scan_mode` | Barcode picking | **MISSING** |
| **Group Same Items** | `pick_list.json:145-148` — `group_same_items` | Consolidation | **MISSING** |
| **Consider Rejected Warehouses** | `pick_list.json:201-205` | QC workflow | **MISSING** |
| **Pick Manually** | `pick_list.json:208-212` | Override capability | **MISSING** |
| **Work Order Link** | `pick_list.json:79-83` | Production picking | **MISSING** |
| **Per Delivered** | `pick_list.json:236-244` | Progress tracking | **MISSING** |

### 3.5 Putaway Rule

| ERPNext Feature | Reference | Epic Coverage | Status in UltrERP |
|-----------------|-----------|---------------|-------------------|
| **Putaway Rule** | `erpnext/stock/doctype/putaway_rule/putaway_rule.json` | Epic 4 | **MISSING** |
| **Item + Warehouse + Company** | `putaway_rule.json:24-80` — composite key | Location assignment | **MISSING** |
| **Capacity** | `putaway_rule.json:52-58, 97-99` — `capacity`, `stock_capacity` | Bin limits | **MISSING** |
| **Priority** | `putaway_rule.json:68-73` — `priority` | Preference ranking | **MISSING** |
| **UOM Conversion** | `putaway_rule.json:90-109` — `uom`, `conversion_factor` | Multi-unit storage | **MISSING** |
| **Auto-Apply on Receipt** | `stock_entry.json:627-631` — `apply_putaway_rule` | Epic 4 | **MISSING** |

### 3.6 Serial and Batch

| ERPNext Feature | Reference | Epic Coverage | Status in UltrERP |
|-----------------|-----------|---------------|-------------------|
| **Serial No** | `erpnext/stock/doctype/serial_no/serial_no.json` | Epic 4/27 | **MISSING** |
| **Batch** | `erpnext/stock/doctype/batch/batch.json` | Epic 4 | **MISSING** |
| **Manufacturing Date** | Batch `manufacturing_date` | Production tracking | **MISSING** |
| **Expiry Date** | `batch.json` — `expiry_date` | Shelf life | **MISSING** |
| **Batch Qty** | `batch.json` — `batch_qty` | Quantity tracking | **MISSING** |
| **Use Batchwise Valuation** | `batch.json` — `use_batchwise_valuation` | Per-batch costing | **MISSING** |
| **Serial and Batch Bundle** | `erpnext/stock/doctype/serial_and_batch_bundle/serial_and_batch_bundle.json` | Central aggregation | **MISSING** |
| **Auto Create Batch** | `item.json:450-461` — `create_new_batch`, `batch_number_series` | Auto-generation | **MISSING** |
| **Shelf Life in Days** | `item.json:337-342` — `shelf_life_in_days` | Expiry calculation | **MISSING** |
| **Retain Sample** | `item.json:473-485` — `retain_sample`, `sample_quantity` | QA sampling | **MISSING** |
| **Has Serial No** | `item.json:492-506` — `has_serial_no`, `serial_no_series` | Serial tracking | **MISSING** |
| **Has Batch No** | `item.json:439-461` — `has_batch_no`, `batch_number_series` | Lot tracking | **MISSING** |
| **Has Expiry Date** | `item.json:464-469` — `has_expiry_date` | Shelf life management | **MISSING** |

### 3.7 Item Variant (Attributes)

| ERPNext Feature | Reference | Epic Coverage | Status in UltrERP |
|-----------------|-----------|---------------|-------------------|
| **Item Variant Settings** | `erpnext/stock/doctype/item_variant_settings/item_variant_settings.json` | Epic 4 | **MISSING** |
| **Variant of** | `item.json:157-168` — `variant_of` | Template inheritance | **MISSING** |
| **Has Variants** | `item.json:516-524` — `has_variants` | Configuration flag | **MISSING** |
| **Variant Based On** | `item.json:526-531` — `variant_based_on` | Attribute/Manufacturer | **MISSING** |
| **Variant Attributes** | `item.json:534-541` — `attributes` table | Dimension values | **MISSING** |
| **Item Attribute** | `erpnext/setup/doctype/item_attribute/item_attribute.json` | Attribute definition | **MISSING** |
| **Item Attribute Value** | `erpnext/setup/doctype/item_attribute_item/item_attribute_item.json` | Valid values | **MISSING** |
| **Numeric Range Attributes** | Item Attribute with `numeric_values` | Continuous dimensions | **MISSING** |
| **Auto-generate Variants** | Variant generation logic | Configuration wizard | **MISSING** |

### 3.8 Landed Cost Wizard

| ERPNext Feature | Reference | Epic Coverage | Status in UltrERP |
|-----------------|-----------|---------------|-------------------|
| **Landed Cost Voucher** | `erpnext/stock/doctype/landed_cost_voucher/landed_cost_voucher.json` | Epic 4 | **MISSING** |
| **Vendor Invoices** | `landed_cost_voucher.json:146-149` — `vendor_invoices` | Freight charges | **MISSING** |
| **Purchase Receipts** | `landed_cost_voucher.json:52-56` — `purchase_receipts` | Receipt linking | **MISSING** |
| **Distribute by Qty** | `landed_cost_voucher.json:105-109` — Qty option | Proportional allocation | **MISSING** |
| **Distribute by Amount** | `landed_cost_voucher.json:105-109` — Amount option | Value-based allocation | **MISSING** |
| **Distribute Manually** | `landed_cost_voucher.json:105-109` — Manual option | Custom allocation | **MISSING** |
| **Landed Cost Taxes and Charges** | `landed_cost_voucher.json:82-86` — `taxes` | Charge breakdown | **MISSING** |
| **Update Item Valuation** | Landed cost → Stock valuation | Epic 4 | **MISSING** |

### 3.9 What's Missing (Inventory)

| Feature | Gap Severity | Business Impact |
|---------|--------------|-----------------|
| Stock Reconciliation with barcode scanning | High | Cannot perform physical counts |
| Landed Cost Voucher | High | Cannot absorb shipping/duties into product cost |
| Putaway Rules | Medium | No intelligent storage assignment |
| Pick List | High | Cannot optimize order picking |
| Serial/Batch tracking | High | Regulatory compliance gap |
| Item Variants | High | Cannot handle product configurations |
| Stock Entry 13 purpose types | High | Cannot execute manufacturing workflows |
| Quality Inspection | High | Cannot perform incoming/outgoing QC |

---

## 4. Subcontracting (Epic 24 + 32 Coverage)

### 4.1 ERPNext Subcontracting Workflow

```
Purchase Order (with fg_item/fg_item_qty)
        ↓
Subcontracting Order (auto-created or manual)
        ↓
Material Transfer to Job Worker (Stock Entry: Send to Subcontractor)
        ↓
Subcontracting Receipt (receives FG, tracks consumed materials)
        ↓
Purchase Invoice (for service charges)
```

### 4.2 BOM for Subcontracting

| ERPNext Feature | Reference | Epic 32 Alignment | Status in UltrERP |
|-----------------|-----------|-------------------|-------------------|
| **Item: Is Subcontracted** | `item.json:791-797` — `is_sub_contracted_item` | Outsourcing flag | **MISSING** |
| **BOM for Subcontracted Item** | Standard BOM with Item set as subcontracted | Process definition | **MISSING** |
| **BOM Operation: Is Subcontracted** | `bom_operation.json:271-274` — `is_subcontracted` | Partial outsourcing | **MISSING** |
| **Supplied Items in BOM** | BOM with `item`, `qty`, `stock_qty` | Component specification | **MISSING** |

### 4.3 Material Transfer to Subcontractor

| ERPNext Feature | Reference | Epic 32 Alignment | Status in UltrERP |
|-----------------|-----------|-------------------|-------------------|
| **Send to Subcontractor** | Stock Entry purpose | Material transfer | **MISSING** |
| **Supplier Warehouse** | Stock Entry → subcontracting flow | Job worker location | **MISSING** |
| **Supplied Items Tracking** | `subcontracting_order.json:335-342` | BOM component reservation | **MISSING** |
| **Reserve Stock** | `subcontracting_order.json:479-483` — `reserve_stock` | Inventory control | **MISSING** |
| **Partial Transfer** | Stock Entry → `per_transferred` | Staged shipments | **MISSING** |

### 4.4 Service Receipt

| ERPNext Feature | Reference | Epic 32 Alignment | Status in UltrERP |
|-----------------|-----------|-------------------|-------------------|
| **Subcontracting Receipt** | `erpnext/subcontracting/doctype/subcontracting_receipt/subcontracting_receipt.json` | FG return recording | **MISSING** |
| **Items Table** | `subcontracting_receipt.json:287-293` — finished goods received | Product receipt | **MISSING** |
| **Consumed Items** | `subcontracting_receipt.json:315-321` — `supplied_items` | Material usage tracking | **MISSING** |
| **Rejected Warehouse** | `subcontracting_receipt.json:257-266` | Defective handling | **MISSING** |
| **Accepted Warehouse** | `subcontracting_receipt.json:249-254` — `set_warehouse` | FG storage | **MISSING** |
| **Job Worker Delivery Note** | `subcontracting_receipt.json:635-637` — `supplier_delivery_note` | Reference tracking | **MISSING** |
| **Vehicle Number** | `subcontracting_receipt.json:508-513` — `lr_no`, `lr_date` | Logistics tracking | **MISSING** |
| **Is Return** | `subcontracting_receipt.json:545-561` | Return handling | **MISSING** |
| **Additional Costs** | `subcontracting_receipt.json:601-624` — `additional_costs` | Extra charges | **MISSING** |
| **Distribute Costs** | `subcontracting_receipt.json:607-610` — Qty/Amount | Cost allocation | **MISSING** |

### 4.5 Subcontracting Order Details

| ERPNext Feature | Reference | Epic 32 Alignment | Status in UltrERP |
|-----------------|-----------|-------------------|-------------------|
| **Subcontracting Order** | `erpnext/subcontracting/doctype/subcontracting_order/subcontracting_order.json` | Job work order | **MISSING** |
| **Job Worker (Supplier)** | `subcontracting_order.json:98-107` — `supplier` | Subcontractor reference | **MISSING** |
| **Job Worker Warehouse** | `subcontracting_order.json:120-125` — `supplier_warehouse` | Material destination | **MISSING** |
| **Purchase Order Link** | `subcontracting_order.json:91-96` — `purchase_order` | Legal binding | **MISSING** |
| **Service Items** | `subcontracting_order.json:306-317` — processing charges | Service cost tracking | **MISSING** |
| **Total Qty / Total** | `subcontracting_order.json:284-301` | Order values | **MISSING** |
| **Per Received** | `subcontracting_order.json:386-394` — `per_received` | Progress tracking | **MISSING** |
| **Address/Contact** | `subcontracting_order.json:174-252` — full contact management | Communication | **MISSING** |
| **Shipping Address** | `subcontracting_order.json:228-240` — `shipping_address` | Delivery destination | **MISSING** |

### 4.6 Epic 24 + 32 vs ERPNext Summary

| Epic 24/32 Capability | ERPNext Coverage | Gap Severity |
|-----------------------|------------------|--------------|
| Supplier Scoring | Supplier Scorecard | Complete |
| Blanket Orders | Blanket Order | Complete |
| Request for Quotation | RFQ + Supplier Quotation | Complete |
| Subcontracting Order | Subcontracting Order + Receipt | Complete |
| Material Transfer to Subcontractor | Stock Entry + Subcontracting Order | Complete |
| Job Worker Management | Supplier as Job Worker | Complete |
| Subcontracting BOM | BOM + Item subcontracted flag | Complete |
| Cost Plus Subcontracting | Additional Costs + Distribution | Complete |
| Drop Ship | Delivered by Supplier flag | Complete |

**What's covered:**
- ERPNext has **complete** Epic 24 purchasing coverage (RFQ, Supplier Quotation, PO, Receipt, Invoice)
- ERPNext has **complete** Epic 32 subcontracting coverage (orders, receipts, material tracking)
- ERPNext has **excellent** Supplier Scorecard for vendor management

**What's missing (UltrERP):**
- Everything Epic 24 + 32 — no PO, PR, RFQ, Supplier Scorecard, Subcontracting, or Drop Ship

---

## 5. Taiwan-Specific Enhancements for UltrERP

Based on analysis of Taiwan manufacturing requirements, ERPNext gaps, and UltrERP's positioning, the following **Taiwan-specific enhancements** are recommended:

### 5.1 Mandatory Enhancements (Taiwan Manufacturing Compliance)

| Enhancement | Description | Rationale |
|-------------|-------------|-----------|
| **eGUI Invoice Auto-Generation from Sales** | Auto-generate Taiwan eGUI when Sales Invoice is completed | Taiwan legal requirement for B2B invoicing |
| **eGUI Linking to Delivery Notes** | Link eGUI sequence numbers to DN for traceability | Tax audit compliance |
| **e-Invoice Ready Workflow** | Integration point for Taiwan e-invoice platform | Mandatory for >NT$50K transactions |
| **Business Entity Validation (TW)** | Taiwan Company Unified Business No. (統一編號) checksum validation | Ensure valid supplier/customer codes |
| **Chinese Character Support** | Full Traditional Chinese in all forms/reports | Native language requirement |
| **Taiwan Tax Integration** | 5% VAT, dual tax rates (taxed/tax-exempt) | Taiwan tax law compliance |
| **Currency: TWD Default** | New Taiwan Dollar as default with proper formatting | Taiwan market default |
| **ROC Address Format** | Zip code + City + District + Address format | Taiwan address standard |

### 5.2 Quality Management Enhancements (Beyond ERPNext)

| Enhancement | Description | Rationale |
|-------------|-------------|-----------|
| **ISO 9001 Document Control Integration** | Quality Procedures with version control and approval workflow | Taiwan exporters need ISO certification |
| **AQL Sampling Tables** | Automatic sample size calculation based on AQL levels | QC standard in electronics/manufacturing |
| **SPC Charts (Statistical Process Control)** | X-bar, R charts with control limits | Process capability monitoring |
| **Gauge Management** | Gauge calibration schedule and records | Measurement system compliance |
| **Supplier Quality Scorecard** | Aggregated supplier quality metrics | Vendor development programs |
| **Material Review Board (MRB)** | Formal review workflow for non-conforming materials | Engineering change control |
| **8D Problem Solving** | Structured 8 Disciplines format for NCR | Customer requirement (especially automotive) |
| **FMEA Integration** | Link Quality Procedures to Failure Mode Effects Analysis | Design control for medical/devices |

### 5.3 Manufacturing Enhancements (Taiwan SME Focus)

| Enhancement | Description | Rationale |
|-------------|-------------|-----------|
| **Short-Run Production Mode** | Simplified WO for small batch production common in Taiwan | Taiwan SME use case |
| **Quick WO from Sales Order** | One-click Work Order creation from confirmed SO | Speed for make-to-order |
| **Kanban Card Printing** | Print Kanban cards from Pick List | Pull-based production |
| **Multi-Unit Production** | Produce multiple SKUs in single WO | Taiwan contract manufacturing |
| **Tooling/Jig Tracking** | Track production tooling with maintenance schedule | Reduce downtime |
| **Downtime Recording** | Quick downtime reason entry during production | OEE calculation |
| **Andon Light Integration** | API for IoT light towers | Shop floor automation |
| **MES Integration API** | Standard interface for shop floor systems | Industry 4.0 readiness |

### 5.4 Inventory Enhancements (Taiwan Logistics)

| Enhancement | Description | Rationale |
|-------------|-------------|-----------|
| **3PL Integration API** | Standard interface for third-party logistics | Taiwan logistics providers |
| **GS1 Barcode Support** | Taiwan requires GS1-128 for certain products | Export compliance |
| **Lot Traceability Report** | One-click traceability from raw material to finished goods | Recall management |
| **Cross-Docking Support** | Rapid putaway for distribution centers | Taiwan retail/distribution |
| **ABC Analysis with Cost** | Inventory classification with revenue impact | Working capital optimization |
| **Safety Stock Optimization** | Calculate safety stock based on demand variability | Service level optimization |
| **Warehouse Zone Management** | Define zones (Receiving, QC Hold, Picking, Shipping) | Warehouse operations |
| **Rejection Tag Printing** | QR code tag for rejected materials | QC workflow |

### 5.5 Subcontracting Enhancements (Taiwan Job Workers)

| Enhancement | Description | Rationale |
|-------------|-------------|-----------|
| **Job Worker Portal** | Web portal for suppliers to view orders and submit receipts | Taiwan subcontracting model |
| **BOM Revision Control** | Track BOM version sent to job worker | Engineering change control |
| **Material Consumption Report** | Per-job-worker consumption vs BOM comparison | Yield tracking |
| **Tooling at Subcontractor** | Track tooling lent to job workers | Asset management |
| **Quality Hold at Subcontractor** | Flag materials awaiting QC at job worker | Process control |
| **Partial Receipt with Yield** | Allow short receipts with yield documentation | Manufacturing reality |
| **Job Worker Performance Scorecard** | On-time, quality, cost metrics | Supplier development |

---

## 6. Implementation Story Recommendations

### Priority 1: Foundation (3-4 months)

#### Epic 27 Foundation Stories

- [ ] **Story: BOM Master** — Create Bill of Materials doctype with items table, operations table, costing, quality inspection link, scrap warehouse
- [ ] **Story: Work Order Lifecycle** — Create Work Order doctype with status machine, BOM link, warehouse configuration, production tracking
- [ ] **Story: Stock Entry Manufacturing** — Implement Manufacture, Material Transfer for Manufacture, Repack purposes; process loss tracking
- [ ] **Story: Quality Inspection Templates** — Create QI Template with inspection parameters, acceptance criteria
- [ ] **Story: Quality Inspection Recording** — Create QI doctype linked to PR/DN/SE; acceptance/rejection workflow

#### Epic 29 Foundation Stories

- [ ] **Story: NCR Workflow** — Create Non-Conformance doctype with procedure link, corrective/preventive action, status tracking
- [ ] **Story: Quality Action (CAPA)** — Create Quality Action doctype with resolutions, review linkage, goal tracking
- [ ] **Story: Quality Procedure Tree** — Create Quality Procedure doctype with tree structure, process steps, owner assignment
- [ ] **Story: Quality Goals** — Create Quality Goal doctype with objectives, monitoring frequency, KPI tracking

#### Epic 4 Foundation Stories

- [ ] **Story: Stock Reconciliation** — Implement physical count workflow with scan mode, barcode support, variance posting
- [ ] **Story: Pick List** — Create Pick List doctype for Delivery/Transfer/Manufacturing purposes; scan mode support
- [ ] **Story: Landed Cost Wizard** — Create LCV doctype with vendor invoices, receipt linking, distribution methods
- [ ] **Story: Putaway Rules** — Create Putaway Rule doctype with capacity, priority, auto-apply on receipt

### Priority 2: Advanced Manufacturing (2-3 months)

- [ ] **Story: Production Plan** — Implement Production Plan from Sales Orders/Material Requests; auto-create Work Orders
- [ ] **Story: Job Cards** — Create Job Card doctype with time logs, workstation assignment, employee tracking
- [ ] **Story: Routing Master** — Create Routing doctype with operation sequences; BOM operation link
- [ ] **Story: Workstation** — Create Workstation and Workstation Type doctypes; working hours calendar
- [ ] **Story: Downtime Tracking** — Implement Downtime Entry doctype linked to Workstation; OEE calculation
- [ ] **Story: Multi-Level BOM** — Implement BOM explosion for sub-assemblies; use_multi_level_bom logic
- [ ] **Story: Process Loss** — Track process loss percentage and qty in BOM and Stock Entry; cost adjustment

### Priority 3: Serial/Batch & Variants (2 months)

- [ ] **Story: Serial Number Tracking** — Create Serial No doctype; status tracking (Active/Consumed/Delivered); warranty expiry
- [ ] **Story: Batch Management** — Create Batch doctype with manufacturing/expiry dates; batchwise valuation
- [ ] **Story: Serial and Batch Bundle** — Central aggregation doctype for serial/batch per transaction row
- [ ] **Story: Item Variants** — Implement variant generation from Item Attributes; template inheritance
- [ ] **Story: AQL Sampling** — Add automatic sample size calculation based on AQL inspection levels

### Priority 4: Subcontracting (2 months)

- [ ] **Story: Subcontracting Order** — Create Subcontracting Order doctype with job worker, service items, supplied items
- [ ] **Story: Material Transfer to Job Worker** — Stock Entry: Send to Subcontractor; reserve stock tracking
- [ ] **Story: Subcontracting Receipt** — Create Subcontracting Receipt doctype; consumed items, rejected warehouse, yield tracking
- [ ] **Story: BOM Subcontracting** — Mark Item as subcontracted; BOM operation subcontracted flag

### Priority 5: Taiwan-Specific Enhancements (Ongoing)

- [ ] **Story: Taiwan eGUI Integration** — Auto-generate eGUI from Sales Invoice; delivery note linking
- [ ] **Story: Taiwan Tax Calculation** — 5% VAT, taxed/tax-exempt toggle, tax reporting
- [ ] **Story: Taiwan Address Format** — ROC address format with zip code validation
- [ ] **Story: Lot Traceability Report** — Full traceability from raw material to finished goods
- [ ] **Story: Supplier Quality Scorecard** — Aggregated QI metrics per supplier
- [ ] **Story: ISO Document Control** — Version control for Quality Procedures with approval workflow

---

## 7. Verification Criteria

### BOM + Work Order Verification
- [ ] Can create BOM with multiple items and operations
- [ ] Can create Work Order from BOM
- [ ] Can transfer materials via Stock Entry
- [ ] Can manufacture FG and update Work Order status
- [ ] Can handle scrap/reject in manufacture entry

### Quality Inspection Verification
- [ ] QI Template can define multiple parameters with acceptance criteria
- [ ] QI can be triggered from PR (incoming) and DN (outgoing)
- [ ] Rejected QI prevents transaction completion
- [ ] NCR can be created from rejected QI
- [ ] Quality Action can be linked to NCR with resolutions

### Stock Operations Verification
- [ ] Pick List can be created from Sales Order
- [ ] Pick List supports barcode scanning
- [ ] Stock Reconciliation can perform physical count
- [ ] Putaway Rule auto-suggests storage location on receipt
- [ ] Landed Cost Voucher distributes freight across receipt items

### Subcontracting Verification
- [ ] Subcontracting Order can be created with supplied items
- [ ] Material Transfer to Job Worker updates reserved quantity
- [ ] Subcontracting Receipt records consumed materials
- [ ] Partial receipts are tracked with per_received percentage

### Taiwan Compliance Verification
- [ ] eGUI is auto-generated on Sales Invoice completion
- [ ] Taiwan tax (5%) is correctly calculated
- [ ] Address format supports ROC standard with zip code
- [ ] Lot traceability shows full genealogy

---

## 8. Technical Considerations

### 8.1 BOM Structure

ERPNext's BOM is complex with 775-line JSON. Minimum viable:
```json
{
  "item": "FG-001",
  "quantity": 10,
  "items": [
    {"item_code": "RM-001", "qty": 5, "stock_qty": 5},
    {"item_code": "RM-002", "qty": 2, "stock_qty": 2}
  ],
  "operations": [
    {"operation": "Assembly", "workstation": "WS-001", "time_in_mins": 30}
  ],
  "inspection_required": true,
  "quality_inspection_template": "QIT-001"
}
```

### 8.2 Quality Inspection Integration

Quality Inspection should gate:
1. **Purchase Receipt** → If `item.inspection_required_before_purchase` → Require QI before stock update
2. **Delivery Note** → If `item.inspection_required_before_delivery` → Require QI before shipment
3. **Job Card** → If `bom_operation.quality_inspection_required` → Require QI for operation completion

### 8.3 Stock Ledger Entry

All stock movements must create SLE:
```json
{
  "voucher_type": "Stock Entry",
  "voucher_no": "STE-001",
  "item_code": "RM-001",
  "warehouse": "WH-001",
  "stock_uom": "Nos",
  "qty": 10,
  "incoming_rate": 100,
  "valuation_rate": 100,
  "batch_no": "BATCH-001",
  "serial_no": "SN-001"
}
```

### 8.4 Subcontracting Data Flow

```
PO (supplier = Job Worker, fg_item = Subcontracted FG)
    ↓
SCO (Subcontracting Order) — auto-created or manual
    ↓
STE (Send to Subcontractor) — deducts from WH, reserves to job worker
    ↓
SCR (Subcontracting Receipt) — receives FG, tracks consumed RMs
    ↓
PI (Purchase Invoice) — pays for processing service
```

---

## 9. Alternative Approaches

### Approach A: Phased ERPnext Alignment (Recommended)
Build features in ERPNext's image, adding Taiwan-specific enhancements on top. Maximum compatibility with existing knowledge base, faster implementation.

### Approach B: Taiwan-First Design
Design for Taiwan requirements first, then extend to ERPNext compatibility. Better differentiation but slower initial development.

### Approach C: Hybrid with ERPnext Reference
Use ERPNext as architectural reference only; implement custom domain models that happen to be compatible. Maximum flexibility but requires more design decisions.

**Recommendation:** Approach A — Phase 1 implements ERPNext-style workflows with Taiwan tax/address compliance; Phase 2 adds Taiwan-specific QC enhancements.

---

## Appendix: File Reference Map

| ERPNext File | Purpose | Priority |
|--------------|---------|----------|
| `erpnext/manufacturing/doctype/bom/bom.json` | BOM definition | P1 |
| `erpnext/manufacturing/doctype/work_order/work_order.json` | Production order | P1 |
| `erpnext/manufacturing/doctype/job_card/job_card.json` | Operation execution | P2 |
| `erpnext/manufacturing/doctype/production_plan/production_plan.json` | Planning aggregation | P2 |
| `erpnext/stock/doctype/stock_entry/stock_entry.json` | All stock movements | P1 |
| `erpnext/stock/doctype/quality_inspection/quality_inspection.json` | QC recording | P1 |
| `erpnext/stock/doctype/landed_cost_voucher/landed_cost_voucher.json` | Freight allocation | P1 |
| `erpnext/stock/doctype/pick_list/pick_list.json` | Order picking | P1 |
| `erpnext/stock/doctype/putaway_rule/putaway_rule.json` | Storage assignment | P1 |
| `erpnext/stock/doctype/stock_reconciliation/stock_reconciliation.json` | Physical count | P1 |
| `erpnext/quality_management/doctype/non_conformance/non_conformance.json` | NCR tracking | P1 |
| `erpnext/quality_management/doctype/quality_action/quality_action.json` | CAPA | P1 |
| `erpnext/subcontracting/doctype/subcontracting_order/subcontracting_order.json` | Job work orders | P4 |
| `erpnext/subcontracting/doctype/subcontracting_receipt/subcontracting_receipt.json` | FG receipts | P4 |
