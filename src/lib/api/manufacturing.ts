/** Manufacturing API client - BOM, Work Orders, Routing, Workstations, Production Planning, and OEE. */

import type {
	BomCreatePayload,
	BomListResponse,
	BomResponse,
	BomSubmitPayload,
	BomSupersedePayload,
	BomUpdatePayload,
	DowntimeCreatePayload,
	DowntimeParetoResponse,
	DowntimeResponse,
	ListResponse,
	ManufacturingProposalResponse,
	OeeDashboardResponse,
	OeeRecordCreatePayload,
	OeeRecordResponse,
	ProductionPlanCreatePayload,
	ProductionPlanFirmPayload,
	ProductionPlanListResponse,
	ProductionPlanResponse,
	ProposalDecisionPayload,
	ProposalGeneratePayload,
	RoutingCalculationResult,
	RoutingCreatePayload,
	RoutingListResponse,
	RoutingResponse,
	RoutingUpdatePayload,
	WorkOrderCompletePayload,
	WorkOrderCreatePayload,
	WorkOrderListResponse,
	WorkOrderResponse,
	WorkOrderReservePayload,
	WorkOrderStatusTransitionPayload,
	WorkOrderTransferPayload,
	WorkOrderUpdatePayload,
	WorkstationCreatePayload,
	WorkstationListResponse,
	WorkstationResponse,
	WorkstationUpdatePayload,
} from "../../domain/manufacturing/types";
import { apiFetch } from "../apiFetch";

// ---------------------------------------------------------------------------
// Error helper
// ---------------------------------------------------------------------------

async function parseErrorMessage(resp: Response, fallback: string): Promise<string> {
	try {
		const body = await resp.json();
		if (Array.isArray(body?.detail)) return body.detail[0]?.message ?? fallback;
		if (typeof body?.detail === "string") return body.detail;
	} catch {
		// ignore parse errors
	}
	return fallback;
}

// ---------------------------------------------------------------------------
// BOM API
// ---------------------------------------------------------------------------

export async function createBom(payload: BomCreatePayload): Promise<BomResponse> {
	const resp = await apiFetch("/api/v1/manufacturing/boms", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to create BOM"));
	return resp.json();
}

export async function listBoms(params?: {
	product_id?: string;
	status?: string;
	is_active?: boolean;
	page?: number;
	page_size?: number;
}): Promise<ListResponse<BomListResponse>> {
	const qs = new URLSearchParams();
	if (params?.product_id) qs.set("product_id", params.product_id);
	if (params?.status) qs.set("status", params.status);
	if (params?.is_active !== undefined) qs.set("is_active", String(params.is_active));
	if (params?.page) qs.set("page", String(params.page));
	if (params?.page_size) qs.set("page_size", String(params.page_size));
	const resp = await apiFetch(`/api/v1/manufacturing/boms?${qs}`);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to list BOMs"));
	return resp.json();
}

export async function getBom(bomId: string): Promise<BomResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/boms/${bomId}`);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load BOM"));
	return resp.json();
}

export async function updateBom(bomId: string, payload: BomUpdatePayload): Promise<BomResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/boms/${bomId}`, {
		method: "PATCH",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to update BOM"));
	return resp.json();
}

export async function submitBom(bomId: string, payload?: BomSubmitPayload): Promise<BomResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/boms/${bomId}/submit`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload || {}),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to submit BOM"));
	return resp.json();
}

export async function supersedeBom(
	bomId: string,
	replacementBomId: string,
	payload?: BomSupersedePayload,
): Promise<BomResponse> {
	const resp = await apiFetch(
		`/api/v1/manufacturing/boms/${bomId}/supersede?replacement_bom_id=${replacementBomId}`,
		{
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(payload || {}),
		},
	);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to supersede BOM"));
	return resp.json();
}

export async function getProductBomHistory(productId: string): Promise<BomListResponse[]> {
	const resp = await apiFetch(`/api/v1/manufacturing/products/${productId}/bom-history`);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load BOM history"));
	return resp.json();
}

export async function getActiveBom(productId: string): Promise<BomResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/products/${productId}/active-bom`);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load active BOM"));
	return resp.json();
}

// ---------------------------------------------------------------------------
// Work Order API
// ---------------------------------------------------------------------------

export async function createWorkOrder(payload: WorkOrderCreatePayload): Promise<WorkOrderResponse> {
	const resp = await apiFetch("/api/v1/manufacturing/work-orders", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to create work order"));
	return resp.json();
}

export async function listWorkOrders(params?: {
	status?: string;
	product_id?: string;
	page?: number;
	page_size?: number;
}): Promise<ListResponse<WorkOrderListResponse>> {
	const qs = new URLSearchParams();
	if (params?.status) qs.set("status", params.status);
	if (params?.product_id) qs.set("product_id", params.product_id);
	if (params?.page) qs.set("page", String(params.page));
	if (params?.page_size) qs.set("page_size", String(params.page_size));
	const resp = await apiFetch(`/api/v1/manufacturing/work-orders?${qs}`);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to list work orders"));
	return resp.json();
}

export async function getWorkOrder(workOrderId: string): Promise<WorkOrderResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/work-orders/${workOrderId}`);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load work order"));
	return resp.json();
}

export async function updateWorkOrder(
	workOrderId: string,
	payload: WorkOrderUpdatePayload,
): Promise<WorkOrderResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/work-orders/${workOrderId}`, {
		method: "PATCH",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to update work order"));
	return resp.json();
}

export async function transitionWorkOrder(
	workOrderId: string,
	payload: WorkOrderStatusTransitionPayload,
): Promise<WorkOrderResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/work-orders/${workOrderId}/transition`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to transition work order"));
	return resp.json();
}

export async function completeWorkOrder(
	workOrderId: string,
	payload: WorkOrderCompletePayload,
): Promise<WorkOrderResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/work-orders/${workOrderId}/complete`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to complete work order"));
	return resp.json();
}

export async function reserveWorkOrderMaterials(
	workOrderId: string,
	payload: WorkOrderReservePayload,
): Promise<WorkOrderResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/work-orders/${workOrderId}/reserve`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to reserve materials"));
	return resp.json();
}

export async function transferWorkOrderMaterials(
	workOrderId: string,
	payload: WorkOrderTransferPayload,
): Promise<WorkOrderResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/work-orders/${workOrderId}/transfer`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to transfer materials"));
	return resp.json();
}

// ---------------------------------------------------------------------------
// Workstation API
// ---------------------------------------------------------------------------

export async function createWorkstation(payload: WorkstationCreatePayload): Promise<WorkstationResponse> {
	const resp = await apiFetch("/api/v1/manufacturing/workstations", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to create workstation"));
	return resp.json();
}

export async function listWorkstations(params?: {
	status?: string;
	page?: number;
	page_size?: number;
}): Promise<ListResponse<WorkstationListResponse>> {
	const qs = new URLSearchParams();
	if (params?.status) qs.set("status", params.status);
	if (params?.page) qs.set("page", String(params.page));
	if (params?.page_size) qs.set("page_size", String(params.page_size));
	const resp = await apiFetch(`/api/v1/manufacturing/workstations?${qs}`);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to list workstations"));
	return resp.json();
}

export async function getWorkstation(workstationId: string): Promise<WorkstationResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/workstations/${workstationId}`);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load workstation"));
	return resp.json();
}

export async function updateWorkstation(
	workstationId: string,
	payload: WorkstationUpdatePayload,
): Promise<WorkstationResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/workstations/${workstationId}`, {
		method: "PATCH",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to update workstation"));
	return resp.json();
}

// ---------------------------------------------------------------------------
// Routing API
// ---------------------------------------------------------------------------

export async function createRouting(payload: RoutingCreatePayload): Promise<RoutingResponse> {
	const resp = await apiFetch("/api/v1/manufacturing/routings", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to create routing"));
	return resp.json();
}

export async function listRoutings(params?: {
	status?: string;
	page?: number;
	page_size?: number;
}): Promise<ListResponse<RoutingListResponse>> {
	const qs = new URLSearchParams();
	if (params?.status) qs.set("status", params.status);
	if (params?.page) qs.set("page", String(params.page));
	if (params?.page_size) qs.set("page_size", String(params.page_size));
	const resp = await apiFetch(`/api/v1/manufacturing/routings?${qs}`);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to list routings"));
	return resp.json();
}

export async function getRouting(routingId: string): Promise<RoutingResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/routings/${routingId}`);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load routing"));
	return resp.json();
}

export async function updateRouting(
	routingId: string,
	payload: RoutingUpdatePayload,
): Promise<RoutingResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/routings/${routingId}`, {
		method: "PATCH",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to update routing"));
	return resp.json();
}

export async function calculateRouting(routingId: string, quantity: number): Promise<RoutingCalculationResult> {
	const resp = await apiFetch(
		`/api/v1/manufacturing/routings/${routingId}/calculate?quantity=${quantity}`,
	);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to calculate routing"));
	return resp.json();
}

// ---------------------------------------------------------------------------
// Production Planning API
// ---------------------------------------------------------------------------

export async function generateProposals(
	payload?: ProposalGeneratePayload,
): Promise<ManufacturingProposalResponse[]> {
	const resp = await apiFetch("/api/v1/manufacturing/proposals/generate", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload || {}),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to generate proposals"));
	return resp.json();
}

export async function listProposals(params?: {
	status?: string;
	product_id?: string;
	page?: number;
	page_size?: number;
}): Promise<ListResponse<ManufacturingProposalResponse>> {
	const qs = new URLSearchParams();
	if (params?.status) qs.set("status", params.status);
	if (params?.product_id) qs.set("product_id", params.product_id);
	if (params?.page) qs.set("page", String(params.page));
	if (params?.page_size) qs.set("page_size", String(params.page_size));
	const resp = await apiFetch(`/api/v1/manufacturing/proposals?${qs}`);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to list proposals"));
	return resp.json();
}

export async function decideProposal(
	proposalId: string,
	payload: ProposalDecisionPayload,
): Promise<ManufacturingProposalResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/proposals/${proposalId}/decide`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to decide proposal"));
	return resp.json();
}

// ---------------------------------------------------------------------------
// Production Plan API
// ---------------------------------------------------------------------------

export async function createProductionPlan(
	payload: ProductionPlanCreatePayload,
): Promise<ProductionPlanResponse> {
	const resp = await apiFetch("/api/v1/manufacturing/production-plans", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to create production plan"));
	return resp.json();
}

export async function listProductionPlans(params?: {
	status?: string;
	page?: number;
	page_size?: number;
}): Promise<ListResponse<ProductionPlanListResponse>> {
	const qs = new URLSearchParams();
	if (params?.status) qs.set("status", params.status);
	if (params?.page) qs.set("page", String(params.page));
	if (params?.page_size) qs.set("page_size", String(params.page_size));
	const resp = await apiFetch(`/api/v1/manufacturing/production-plans?${qs}`);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to list production plans"));
	return resp.json();
}

export async function getProductionPlan(planId: string): Promise<ProductionPlanResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/production-plans/${planId}`);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load production plan"));
	return resp.json();
}

export async function firmProductionPlan(
	planId: string,
	payload?: ProductionPlanFirmPayload,
): Promise<ProductionPlanResponse> {
	const resp = await apiFetch(`/api/v1/manufacturing/production-plans/${planId}/firm`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload || {}),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to firm production plan"));
	return resp.json();
}

// ---------------------------------------------------------------------------
// Downtime API
// ---------------------------------------------------------------------------

export async function createDowntime(payload: DowntimeCreatePayload): Promise<DowntimeResponse> {
	const resp = await apiFetch("/api/v1/manufacturing/downtime", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to create downtime entry"));
	return resp.json();
}

export async function listDowntime(params?: {
	workstation_id?: string;
	start_date?: string;
	end_date?: string;
	reason?: string;
	page?: number;
	page_size?: number;
}): Promise<ListResponse<DowntimeResponse>> {
	const qs = new URLSearchParams();
	if (params?.workstation_id) qs.set("workstation_id", params.workstation_id);
	if (params?.start_date) qs.set("start_date", params.start_date);
	if (params?.end_date) qs.set("end_date", params.end_date);
	if (params?.reason) qs.set("reason", params.reason);
	if (params?.page) qs.set("page", String(params.page));
	if (params?.page_size) qs.set("page_size", String(params.page_size));
	const resp = await apiFetch(`/api/v1/manufacturing/downtime?${qs}`);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to list downtime entries"));
	return resp.json();
}

export async function getDowntimePareto(params?: {
	workstation_id?: string;
	start_date?: string;
	end_date?: string;
}): Promise<DowntimeParetoResponse[]> {
	const qs = new URLSearchParams();
	if (params?.workstation_id) qs.set("workstation_id", params.workstation_id);
	if (params?.start_date) qs.set("start_date", params.start_date);
	if (params?.end_date) qs.set("end_date", params.end_date);
	const resp = await apiFetch(`/api/v1/manufacturing/downtime/pareto?${qs}`);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load downtime Pareto"));
	return resp.json();
}

// ---------------------------------------------------------------------------
// OEE API
// ---------------------------------------------------------------------------

export async function createOeeRecord(payload: OeeRecordCreatePayload): Promise<OeeRecordResponse> {
	const resp = await apiFetch("/api/v1/manufacturing/oee", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to create OEE record"));
	return resp.json();
}

export async function getOeeDashboard(params?: {
	workstation_id?: string;
	start_date?: string;
	end_date?: string;
}): Promise<OeeDashboardResponse> {
	const qs = new URLSearchParams();
	if (params?.workstation_id) qs.set("workstation_id", params.workstation_id);
	if (params?.start_date) qs.set("start_date", params.start_date);
	if (params?.end_date) qs.set("end_date", params.end_date);
	const resp = await apiFetch(`/api/v1/manufacturing/oee/dashboard?${qs}`);
	if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load OEE dashboard"));
	return resp.json();
}
