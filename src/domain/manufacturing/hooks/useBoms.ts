/** Manufacturing domain hooks - BOM, Work Orders, Routing, Workstations, Production Planning, and OEE. */

import { useCallback, useMemo } from "react";
import useSWR, { useSWRConfig } from "swr";

import * as api from "../../../lib/api/manufacturing";
import type {
	BomCreatePayload,
	BomResponse,
	BomSubmitPayload,
	BomSupersedePayload,
	BomUpdatePayload,
	DowntimeCreatePayload,
	DowntimeResponse,
	ManufacturingProposalResponse,
	OeeRecordCreatePayload,
	OeeRecordResponse,
	ProductionPlanCreatePayload,
	ProductionPlanFirmPayload,
	ProductionPlanResponse,
	ProposalDecisionPayload,
	ProposalGeneratePayload,
	RoutingCalculationResult,
	RoutingCreatePayload,
	RoutingResponse,
	RoutingUpdatePayload,
	WorkOrderCompletePayload,
	WorkOrderCreatePayload,
	WorkOrderResponse,
	WorkOrderReservePayload,
	WorkOrderStatusTransitionPayload,
	WorkOrderTransferPayload,
	WorkOrderUpdatePayload,
	WorkstationCreatePayload,
	WorkstationResponse,
	WorkstationUpdatePayload,
} from "../types";

// ---------------------------------------------------------------------------
// BOM Hooks
// ---------------------------------------------------------------------------

export function useBoms(params?: {
	product_id?: string;
	status?: string;
	is_active?: boolean;
	page?: number;
	page_size?: number;
}) {
	const key = useMemo(
		() => ["/api/v1/manufacturing/boms", params],
		[params],
	);
	const { data, error, isLoading, mutate } = useSWR(key, () => api.listBoms(params));

	return {
		boms: data?.items ?? [],
		total: data?.total ?? 0,
		isLoading,
		isError: error,
		refresh: mutate,
	};
}

export function useBom(bomId: string | null) {
	const { data, error, isLoading, mutate } = useSWR(
		bomId ? `/api/v1/manufacturing/boms/${bomId}` : null,
		() => api.getBom(bomId!),
	);

	return {
		bom: data,
		isLoading,
		isError: error,
		refresh: mutate,
	};
}

export function useBomHistory(productId: string | null) {
	const { data, error, isLoading, mutate } = useSWR(
		productId ? `/api/v1/manufacturing/products/${productId}/bom-history` : null,
		() => api.getProductBomHistory(productId!),
	);

	return {
		history: data ?? [],
		isLoading,
		isError: error,
		refresh: mutate,
	};
}

export function useActiveBom(productId: string | null) {
	const { data, error, isLoading, mutate } = useSWR(
		productId ? `/api/v1/manufacturing/products/${productId}/active-bom` : null,
		() => api.getActiveBom(productId!),
	);

	return {
		activeBom: data,
		isLoading,
		isError: error,
		refresh: mutate,
	};
}

export function useBomActions() {
	const { mutate } = useSWRConfig();

	const createBom = useCallback(async (payload: BomCreatePayload): Promise<BomResponse> => {
		const result = await api.createBom(payload);
		mutate((key) => Array.isArray(key) && key[0]?.includes?.("/api/v1/manufacturing/boms"));
		return result;
	}, [mutate]);

	const updateBom = useCallback(async (bomId: string, payload: BomUpdatePayload): Promise<BomResponse> => {
		const result = await api.updateBom(bomId, payload);
		mutate(`/api/v1/manufacturing/boms/${bomId}`);
		return result;
	}, [mutate]);

	const submitBom = useCallback(async (bomId: string, payload?: BomSubmitPayload): Promise<BomResponse> => {
		const result = await api.submitBom(bomId, payload);
		mutate(`/api/v1/manufacturing/boms/${bomId}`);
		mutate((key) => Array.isArray(key) && key[0]?.includes?.("/api/v1/manufacturing/boms"));
		return result;
	}, [mutate]);

	const supersedeBom = useCallback(
		async (bomId: string, replacementBomId: string, payload?: BomSupersedePayload): Promise<BomResponse> => {
			const result = await api.supersedeBom(bomId, replacementBomId, payload);
			mutate(`/api/v1/manufacturing/boms/${bomId}`);
			mutate((key) => Array.isArray(key) && key[0]?.includes?.("/api/v1/manufacturing/boms"));
			return result;
		},
		[mutate],
	);

	return { createBom, updateBom, submitBom, supersedeBom };
}

// ---------------------------------------------------------------------------
// Work Order Hooks
// ---------------------------------------------------------------------------

export function useWorkOrders(params?: {
	status?: string;
	product_id?: string;
	page?: number;
	page_size?: number;
}) {
	const key = useMemo(
		() => ["/api/v1/manufacturing/work-orders", params],
		[params],
	);
	const { data, error, isLoading, mutate } = useSWR(key, () => api.listWorkOrders(params));

	return {
		workOrders: data?.items ?? [],
		total: data?.total ?? 0,
		isLoading,
		isError: error,
		refresh: mutate,
	};
}

export function useWorkOrder(workOrderId: string | null) {
	const { data, error, isLoading, mutate } = useSWR(
		workOrderId ? `/api/v1/manufacturing/work-orders/${workOrderId}` : null,
		() => api.getWorkOrder(workOrderId!),
	);

	return {
		workOrder: data,
		isLoading,
		isError: error,
		refresh: mutate,
	};
}

export function useWorkOrderActions() {
	const { mutate } = useSWRConfig();

	const createWorkOrder = useCallback(
		async (payload: WorkOrderCreatePayload): Promise<WorkOrderResponse> => {
			const result = await api.createWorkOrder(payload);
			mutate((key) => Array.isArray(key) && key[0]?.includes?.("/api/v1/manufacturing/work-orders"));
			return result;
		},
		[mutate],
	);

	const updateWorkOrder = useCallback(
		async (workOrderId: string, payload: WorkOrderUpdatePayload): Promise<WorkOrderResponse> => {
			const result = await api.updateWorkOrder(workOrderId, payload);
			mutate(`/api/v1/manufacturing/work-orders/${workOrderId}`);
			return result;
		},
		[mutate],
	);

	const transitionWorkOrder = useCallback(
		async (workOrderId: string, payload: WorkOrderStatusTransitionPayload): Promise<WorkOrderResponse> => {
			const result = await api.transitionWorkOrder(workOrderId, payload);
			mutate(`/api/v1/manufacturing/work-orders/${workOrderId}`);
			mutate((key) => Array.isArray(key) && key[0]?.includes?.("/api/v1/manufacturing/work-orders"));
			return result;
		},
		[mutate],
	);

	const completeWorkOrder = useCallback(
		async (workOrderId: string, payload: WorkOrderCompletePayload): Promise<WorkOrderResponse> => {
			const result = await api.completeWorkOrder(workOrderId, payload);
			mutate(`/api/v1/manufacturing/work-orders/${workOrderId}`);
			return result;
		},
		[mutate],
	);

	const reserveMaterials = useCallback(
		async (workOrderId: string, payload: WorkOrderReservePayload): Promise<WorkOrderResponse> => {
			const result = await api.reserveWorkOrderMaterials(workOrderId, payload);
			mutate(`/api/v1/manufacturing/work-orders/${workOrderId}`);
			return result;
		},
		[mutate],
	);

	const transferMaterials = useCallback(
		async (workOrderId: string, payload: WorkOrderTransferPayload): Promise<WorkOrderResponse> => {
			const result = await api.transferWorkOrderMaterials(workOrderId, payload);
			mutate(`/api/v1/manufacturing/work-orders/${workOrderId}`);
			return result;
		},
		[mutate],
	);

	return {
		createWorkOrder,
		updateWorkOrder,
		transitionWorkOrder,
		completeWorkOrder,
		reserveMaterials,
		transferMaterials,
	};
}

// ---------------------------------------------------------------------------
// Workstation Hooks
// ---------------------------------------------------------------------------

export function useWorkstations(params?: { status?: string; page?: number; page_size?: number }) {
	const key = useMemo(
		() => ["/api/v1/manufacturing/workstations", params],
		[params],
	);
	const { data, error, isLoading, mutate } = useSWR(key, () => api.listWorkstations(params));

	return {
		workstations: data?.items ?? [],
		total: data?.total ?? 0,
		isLoading,
		isError: error,
		refresh: mutate,
	};
}

export function useWorkstation(workstationId: string | null) {
	const { data, error, isLoading, mutate } = useSWR(
		workstationId ? `/api/v1/manufacturing/workstations/${workstationId}` : null,
		() => api.getWorkstation(workstationId!),
	);

	return {
		workstation: data,
		isLoading,
		isError: error,
		refresh: mutate,
	};
}

export function useWorkstationActions() {
	const { mutate } = useSWRConfig();

	const createWorkstation = useCallback(
		async (payload: WorkstationCreatePayload): Promise<WorkstationResponse> => {
			const result = await api.createWorkstation(payload);
			mutate((key) => Array.isArray(key) && key[0]?.includes?.("/api/v1/manufacturing/workstations"));
			return result;
		},
		[mutate],
	);

	const updateWorkstation = useCallback(
		async (workstationId: string, payload: WorkstationUpdatePayload): Promise<WorkstationResponse> => {
			const result = await api.updateWorkstation(workstationId, payload);
			mutate(`/api/v1/manufacturing/workstations/${workstationId}`);
			return result;
		},
		[mutate],
	);

	return { createWorkstation, updateWorkstation };
}

// ---------------------------------------------------------------------------
// Routing Hooks
// ---------------------------------------------------------------------------

export function useRoutings(params?: { status?: string; page?: number; page_size?: number }) {
	const key = useMemo(
		() => ["/api/v1/manufacturing/routings", params],
		[params],
	);
	const { data, error, isLoading, mutate } = useSWR(key, () => api.listRoutings(params));

	return {
		routings: data?.items ?? [],
		total: data?.total ?? 0,
		isLoading,
		isError: error,
		refresh: mutate,
	};
}

export function useRouting(routingId: string | null) {
	const { data, error, isLoading, mutate } = useSWR(
		routingId ? `/api/v1/manufacturing/routings/${routingId}` : null,
		() => api.getRouting(routingId!),
	);

	return {
		routing: data,
		isLoading,
		isError: error,
		refresh: mutate,
	};
}

export function useRoutingActions() {
	const { mutate } = useSWRConfig();

	const createRouting = useCallback(
		async (payload: RoutingCreatePayload): Promise<RoutingResponse> => {
			const result = await api.createRouting(payload);
			mutate((key) => Array.isArray(key) && key[0]?.includes?.("/api/v1/manufacturing/routings"));
			return result;
		},
		[mutate],
	);

	const updateRouting = useCallback(
		async (routingId: string, payload: RoutingUpdatePayload): Promise<RoutingResponse> => {
			const result = await api.updateRouting(routingId, payload);
			mutate(`/api/v1/manufacturing/routings/${routingId}`);
			return result;
		},
		[mutate],
	);

	const calculateRouting = useCallback(
		async (routingId: string, quantity: number): Promise<RoutingCalculationResult> => {
			return api.calculateRouting(routingId, quantity);
		},
		[],
	);

	return { createRouting, updateRouting, calculateRouting };
}

// ---------------------------------------------------------------------------
// Production Planning Hooks
// ---------------------------------------------------------------------------

export function useProposals(params?: {
	status?: string;
	product_id?: string;
	page?: number;
	page_size?: number;
}) {
	const key = useMemo(
		() => ["/api/v1/manufacturing/proposals", params],
		[params],
	);
	const { data, error, isLoading, mutate } = useSWR(key, () => api.listProposals(params));

	return {
		proposals: data?.items ?? [],
		total: data?.total ?? 0,
		isLoading,
		isError: error,
		refresh: mutate,
	};
}

export function useProposalActions() {
	const { mutate } = useSWRConfig();

	const generateProposals = useCallback(
		async (payload?: ProposalGeneratePayload): Promise<ManufacturingProposalResponse[]> => {
			const result = await api.generateProposals(payload);
			mutate((key) => Array.isArray(key) && key[0]?.includes?.("/api/v1/manufacturing/proposals"));
			return result;
		},
		[mutate],
	);

	const decideProposal = useCallback(
		async (proposalId: string, payload: ProposalDecisionPayload): Promise<ManufacturingProposalResponse> => {
			const result = await api.decideProposal(proposalId, payload);
			mutate(`/api/v1/manufacturing/proposals/${proposalId}`);
			mutate((key) => Array.isArray(key) && key[0]?.includes?.("/api/v1/manufacturing/proposals"));
			return result;
		},
		[mutate],
	);

	return { generateProposals, decideProposal };
}

// ---------------------------------------------------------------------------
// Production Plan Hooks
// ---------------------------------------------------------------------------

export function useProductionPlans(params?: {
	status?: string;
	page?: number;
	page_size?: number;
}) {
	const key = useMemo(
		() => ["/api/v1/manufacturing/production-plans", params],
		[params],
	);
	const { data, error, isLoading, mutate } = useSWR(key, () => api.listProductionPlans(params));

	return {
		plans: data?.items ?? [],
		total: data?.total ?? 0,
		isLoading,
		isError: error,
		refresh: mutate,
	};
}

export function useProductionPlan(planId: string | null) {
	const { data, error, isLoading, mutate } = useSWR(
		planId ? `/api/v1/manufacturing/production-plans/${planId}` : null,
		() => api.getProductionPlan(planId!),
	);

	return {
		plan: data,
		isLoading,
		isError: error,
		refresh: mutate,
	};
}

export function useProductionPlanActions() {
	const { mutate } = useSWRConfig();

	const createProductionPlan = useCallback(
		async (payload: ProductionPlanCreatePayload): Promise<ProductionPlanResponse> => {
			const result = await api.createProductionPlan(payload);
			mutate((key) => Array.isArray(key) && key[0]?.includes?.("/api/v1/manufacturing/production-plans"));
			return result;
		},
		[mutate],
	);

	const firmProductionPlan = useCallback(
		async (planId: string, payload?: ProductionPlanFirmPayload): Promise<ProductionPlanResponse> => {
			const result = await api.firmProductionPlan(planId, payload);
			mutate(`/api/v1/manufacturing/production-plans/${planId}`);
			mutate((key) => Array.isArray(key) && key[0]?.includes?.("/api/v1/manufacturing/production-plans"));
			return result;
		},
		[mutate],
	);

	return { createProductionPlan, firmProductionPlan };
}

// ---------------------------------------------------------------------------
// Downtime Hooks
// ---------------------------------------------------------------------------

export function useDowntime(params?: {
	workstation_id?: string;
	start_date?: string;
	end_date?: string;
	reason?: string;
	page?: number;
	page_size?: number;
}) {
	const key = useMemo(
		() => ["/api/v1/manufacturing/downtime", params],
		[params],
	);
	const { data, error, isLoading, mutate } = useSWR(key, () => api.listDowntime(params));

	return {
		entries: data?.items ?? [],
		total: data?.total ?? 0,
		isLoading,
		isError: error,
		refresh: mutate,
	};
}

export function useDowntimePareto(params?: {
	workstation_id?: string;
	start_date?: string;
	end_date?: string;
}) {
	const key = useMemo(
		() => ["/api/v1/manufacturing/downtime/pareto", params],
		[params],
	);
	const { data, error, isLoading, mutate } = useSWR(key, () => api.getDowntimePareto(params));

	return {
		pareto: data ?? [],
		isLoading,
		isError: error,
		refresh: mutate,
	};
}

export function useDowntimeActions() {
	const { mutate } = useSWRConfig();

	const createDowntime = useCallback(
		async (payload: DowntimeCreatePayload): Promise<DowntimeResponse> => {
			const result = await api.createDowntime(payload);
			mutate((key) => Array.isArray(key) && key[0]?.includes?.("/api/v1/manufacturing/downtime"));
			return result;
		},
		[mutate],
	);

	return { createDowntime };
}

// ---------------------------------------------------------------------------
// OEE Hooks
// ---------------------------------------------------------------------------

export function useOeeDashboard(params?: {
	workstation_id?: string;
	start_date?: string;
	end_date?: string;
}) {
	const key = useMemo(
		() => ["/api/v1/manufacturing/oee/dashboard", params],
		[params],
	);
	const { data, error, isLoading, mutate } = useSWR(key, () => api.getOeeDashboard(params));

	return {
		dashboard: data,
		isLoading,
		isError: error,
		refresh: mutate,
	};
}

export function useOeeActions() {
	const { mutate } = useSWRConfig();

	const createOeeRecord = useCallback(
		async (payload: OeeRecordCreatePayload): Promise<OeeRecordResponse> => {
			const result = await api.createOeeRecord(payload);
			mutate((key) => Array.isArray(key) && key[0]?.includes?.("/api/v1/manufacturing/oee"));
			return result;
		},
		[mutate],
	);

	return { createOeeRecord };
}
