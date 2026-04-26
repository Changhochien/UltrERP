/** Manufacturing domain types - BOM, Work Orders, Routing, Workstations, Production Planning, and OEE. */

// ---------------------------------------------------------------------------
// BOM Types
// ---------------------------------------------------------------------------

export type BomStatus = "draft" | "submitted" | "inactive" | "superseded";

export interface BomItemPayload {
	item_id: string;
	item_code: string;
	item_name: string;
	required_quantity: string;
	unit?: string;
	source_warehouse_id?: string | null;
	idx?: number;
	notes?: string | null;
}

export interface BomItemResponse {
	id: string;
	tenant_id: string;
	bom_id: string;
	item_id: string;
	item_code: string;
	item_name: string;
	required_quantity: string;
	unit: string;
	source_warehouse_id: string | null;
	idx: number;
	notes: string | null;
	created_at: string;
}

export interface BomCreatePayload {
	product_id: string;
	code?: string;
	name?: string;
	bom_quantity?: string;
	unit?: string;
	revision?: string | null;
	routing_id?: string | null;
	notes?: string | null;
	items: BomItemPayload[];
}

export interface BomUpdatePayload {
	name?: string;
	bom_quantity?: string;
	unit?: string;
	revision?: string | null;
	routing_id?: string | null;
	notes?: string | null;
	items?: BomItemPayload[];
}

export interface BomSubmitPayload {
	notes?: string | null;
}

export interface BomSupersedePayload {
	replacement_bom_id: string;
	notes?: string | null;
}

export interface BomResponse {
	id: string;
	tenant_id: string;
	product_id: string;
	code: string;
	name: string;
	bom_quantity: string;
	unit: string;
	status: BomStatus;
	revision: string | null;
	is_active: boolean;
	supersedes_bom_id: string | null;
	routing_id: string | null;
	notes: string | null;
	submitted_at: string | null;
	submitted_by: string | null;
	created_at: string;
	updated_at: string;
	item_count: number;
	items: BomItemResponse[];
}

export interface BomListResponse {
	id: string;
	tenant_id: string;
	product_id: string;
	code: string;
	name: string;
	bom_quantity: string;
	status: BomStatus;
	revision: string | null;
	is_active: boolean;
	submitted_at: string | null;
	item_count: number;
	created_at: string;
	updated_at: string;
}

// ---------------------------------------------------------------------------
// Work Order Types
// ---------------------------------------------------------------------------

export type WorkOrderStatus =
	| "draft"
	| "submitted"
	| "not_started"
	| "in_progress"
	| "completed"
	| "stopped"
	| "cancelled";

export type WorkOrderTransferMode = "direct" | "manufacture";

export interface WorkOrderMaterialLineResponse {
	id: string;
	tenant_id: string;
	work_order_id: string;
	item_id: string;
	item_code: string;
	item_name: string;
	required_quantity: string;
	unit: string;
	source_warehouse_id: string | null;
	reserved_quantity: string;
	transferred_quantity: string;
	consumed_quantity: string;
	idx: number;
	notes: string | null;
	created_at: string;
}

export interface WorkOrderCreatePayload {
	product_id: string;
	bom_id: string;
	quantity: string;
	source_warehouse_id?: string | null;
	wip_warehouse_id?: string | null;
	fg_warehouse_id?: string | null;
	transfer_mode?: WorkOrderTransferMode;
	planned_start_date?: string | null;
	due_date?: string | null;
	notes?: string | null;
}

export interface WorkOrderUpdatePayload {
	quantity?: string;
	source_warehouse_id?: string | null;
	wip_warehouse_id?: string | null;
	fg_warehouse_id?: string | null;
	transfer_mode?: WorkOrderTransferMode;
	planned_start_date?: string | null;
	due_date?: string | null;
	notes?: string | null;
}

export interface WorkOrderStatusTransitionPayload {
	status: WorkOrderStatus;
	reason?: string | null;
}

export interface WorkOrderCompletePayload {
	produced_quantity: string;
	notes?: string | null;
}

export interface WorkOrderReservePayload {
	action: "reserve" | "release";
	material_line_ids?: string[] | null;
}

export interface WorkOrderTransferPayload {
	material_line_ids?: string[] | null;
	quantity_by_line?: Record<string, string> | null;
}

export interface WorkOrderResponse {
	id: string;
	tenant_id: string;
	code: string;
	name: string;
	product_id: string;
	bom_id: string;
	bom_snapshot: Record<string, unknown> | null;
	quantity: string;
	produced_quantity: string;
	source_warehouse_id: string | null;
	wip_warehouse_id: string | null;
	fg_warehouse_id: string | null;
	status: WorkOrderStatus;
	transfer_mode: WorkOrderTransferMode;
	planned_start_date: string | null;
	due_date: string | null;
	started_at: string | null;
	completed_at: string | null;
	stopped_reason: string | null;
	cancelled_reason: string | null;
	routing_id: string | null;
	routing_snapshot: Record<string, unknown> | null;
	notes: string | null;
	created_at: string;
	updated_at: string;
	material_lines: WorkOrderMaterialLineResponse[];
}

export interface WorkOrderListResponse {
	id: string;
	tenant_id: string;
	code: string;
	name: string;
	product_id: string;
	bom_id: string;
	quantity: string;
	produced_quantity: string;
	status: WorkOrderStatus;
	transfer_mode: WorkOrderTransferMode;
	planned_start_date: string | null;
	due_date: string | null;
	created_at: string;
	updated_at: string;
}

// ---------------------------------------------------------------------------
// Workstation Types
// ---------------------------------------------------------------------------

export type WorkstationStatus = "active" | "disabled";

export interface WorkstationWorkingHourPayload {
	day_of_week: number;
	start_time: string;
	end_time: string;
}

export interface WorkstationCreatePayload {
	code: string;
	name: string;
	description?: string | null;
	hourly_cost?: string;
	capacity?: number;
	hours?: WorkstationWorkingHourPayload[];
}

export interface WorkstationUpdatePayload {
	name?: string;
	description?: string | null;
	hourly_cost?: string;
	capacity?: number;
	disabled?: boolean;
	hours?: WorkstationWorkingHourPayload[] | null;
}

export interface WorkstationResponse {
	id: string;
	tenant_id: string;
	code: string;
	name: string;
	description: string | null;
	status: WorkstationStatus;
	hourly_cost: string;
	capacity: number;
	disabled: boolean;
	created_at: string;
	updated_at: string;
	hours: WorkstationWorkingHourPayload[];
}

export interface WorkstationListResponse {
	id: string;
	tenant_id: string;
	code: string;
	name: string;
	status: WorkstationStatus;
	hourly_cost: string;
	capacity: number;
	disabled: boolean;
	created_at: string;
	updated_at: string;
}

// ---------------------------------------------------------------------------
// Routing Types
// ---------------------------------------------------------------------------

export type RoutingStatus = "draft" | "submitted" | "inactive";

export interface RoutingOperationPayload {
	operation_name: string;
	workstation_id?: string | null;
	sequence: number;
	setup_minutes?: number;
	fixed_run_minutes?: number;
	variable_run_minutes_per_unit?: string;
	batch_size?: number;
	overlap_lag_minutes?: number;
	idx?: number;
	notes?: string | null;
}

export interface RoutingOperationResponse {
	id: string;
	tenant_id: string;
	routing_id: string;
	operation_name: string;
	workstation_id: string | null;
	sequence: number;
	setup_minutes: number;
	fixed_run_minutes: number;
	variable_run_minutes_per_unit: string;
	batch_size: number;
	overlap_lag_minutes: number;
	idx: number;
	notes: string | null;
	created_at: string;
}

export interface RoutingCreatePayload {
	code: string;
	name: string;
	description?: string | null;
	operations?: RoutingOperationPayload[];
}

export interface RoutingUpdatePayload {
	name?: string;
	description?: string | null;
	disabled?: boolean;
	operations?: RoutingOperationPayload[] | null;
}

export interface RoutingResponse {
	id: string;
	tenant_id: string;
	code: string;
	name: string;
	description: string | null;
	status: RoutingStatus;
	disabled: boolean;
	created_at: string;
	updated_at: string;
	operations: RoutingOperationResponse[];
}

export interface RoutingListResponse {
	id: string;
	tenant_id: string;
	code: string;
	name: string;
	status: RoutingStatus;
	disabled: boolean;
	operation_count: number;
	created_at: string;
	updated_at: string;
}

export interface RoutingCalculationResult {
	total_minutes: number;
	total_hours: number;
	total_cost: string;
	operation_count: number;
}

// ---------------------------------------------------------------------------
// Production Planning Types
// ---------------------------------------------------------------------------

export type ManufacturingProposalStatus = "proposed" | "accepted" | "rejected" | "stale";

export interface ProposalGeneratePayload {
	product_ids?: string[] | null;
}

export interface ProposalDecisionPayload {
	decision: "accept" | "reject";
	proposed_quantity?: string | null;
	reason?: string | null;
}

export interface ManufacturingProposalResponse {
	id: string;
	tenant_id: string;
	product_id: string;
	bom_id: string | null;
	demand_source: string;
	demand_source_id: string | null;
	demand_quantity: string;
	proposed_quantity: string;
	available_quantity: string;
	status: ManufacturingProposalStatus;
	decision: string | null;
	decision_reason: string | null;
	decided_by: string | null;
	decided_at: string | null;
	work_order_id: string | null;
	shortages: Array<{
		item_code: string;
		item_name: string;
		required: number;
		available: number;
		shortage: number;
	}> | null;
	notes: string | null;
	created_at: string;
	updated_at: string;
}

// ---------------------------------------------------------------------------
// Production Plan Types
// ---------------------------------------------------------------------------

export type ProductionPlanStatus = "draft" | "reviewed" | "firmed" | "closed";

export interface ProductionPlanLinePayload {
	product_id: string;
	bom_id?: string | null;
	routing_id?: string | null;
	forecast_demand?: string;
	proposed_qty?: string;
	idx?: number;
	notes?: string | null;
}

export interface ProductionPlanLineResponse {
	id: string;
	tenant_id: string;
	plan_id: string;
	product_id: string;
	bom_id: string | null;
	routing_id: string | null;
	sales_order_demand: string;
	forecast_demand: string;
	total_demand: string;
	open_work_order_qty: string;
	available_stock: string;
	proposed_qty: string;
	firmed_qty: string;
	completed_qty: string;
	shortage_summary: Record<string, unknown> | null;
	capacity_summary: Record<string, unknown> | null;
	idx: number;
	notes: string | null;
	created_at: string;
}

export interface ProductionPlanCreatePayload {
	name: string;
	planning_strategy?: string;
	start_date: string;
	end_date: string;
	notes?: string | null;
	lines?: ProductionPlanLinePayload[];
}

export interface ProductionPlanUpdatePayload {
	name?: string;
	planning_strategy?: string;
	start_date?: string;
	end_date?: string;
	notes?: string | null;
}

export interface ProductionPlanFirmPayload {
	line_ids?: string[] | null;
}

export interface ProductionPlanResponse {
	id: string;
	tenant_id: string;
	code: string;
	name: string;
	status: ProductionPlanStatus;
	planning_strategy: string;
	start_date: string;
	end_date: string;
	firmed_at: string | null;
	firmed_by: string | null;
	notes: string | null;
	created_at: string;
	updated_at: string;
	lines: ProductionPlanLineResponse[];
}

export interface ProductionPlanListResponse {
	id: string;
	tenant_id: string;
	code: string;
	name: string;
	status: ProductionPlanStatus;
	planning_strategy: string;
	start_date: string;
	end_date: string;
	line_count: number;
	firmed_at: string | null;
	created_at: string;
	updated_at: string;
}

// ---------------------------------------------------------------------------
// Downtime and OEE Types
// ---------------------------------------------------------------------------

export type DowntimeReason =
	| "planned_maintenance"
	| "unplanned_breakdown"
	| "changeover"
	| "material_shortage"
	| "quality_hold";

export interface DowntimeCreatePayload {
	workstation_id: string;
	work_order_id?: string | null;
	reason: DowntimeReason;
	start_time: string;
	end_time?: string | null;
	remarks?: string | null;
}

export interface DowntimeUpdatePayload {
	work_order_id?: string | null;
	reason?: DowntimeReason | null;
	start_time?: string | null;
	end_time?: string | null;
	remarks?: string | null;
}

export interface DowntimeResponse {
	id: string;
	tenant_id: string;
	workstation_id: string;
	work_order_id: string | null;
	reason: DowntimeReason;
	start_time: string;
	end_time: string | null;
	duration_minutes: number | null;
	remarks: string | null;
	reporter_id: string | null;
	created_at: string;
	updated_at: string;
}

export interface DowntimeParetoResponse {
	reason: DowntimeReason;
	frequency: number;
	total_duration_minutes: number;
	percentage: number;
}

export interface OeeRecordCreatePayload {
	workstation_id: string;
	work_order_id?: string | null;
	record_date: string;
	planned_production_time: number;
	stop_time?: number;
	ideal_cycle_time: number;
	total_count?: number;
	good_count?: number;
	reject_count?: number;
}

export interface OeeRecordResponse {
	id: string;
	tenant_id: string;
	workstation_id: string;
	work_order_id: string | null;
	record_date: string;
	planned_production_time: number;
	stop_time: number;
	run_time: number;
	ideal_cycle_time: number;
	total_count: number;
	good_count: number;
	reject_count: number;
	availability: number;
	performance: number;
	quality: number;
	oee: number;
	created_at: string;
}

export interface OeeDashboardResponse {
	workstation_id: string | null;
	current_oee: number;
	availability: number;
	performance: number;
	quality: number;
	trend_data: OeeRecordResponse[];
	downtime_pareto: DowntimeParetoResponse[];
	period_start: string;
	period_end: string;
}

// ---------------------------------------------------------------------------
// List Response Types
// ---------------------------------------------------------------------------

export interface ListResponse<T> {
	items: T[];
	total: number;
	page: number;
	page_size: number;
}
