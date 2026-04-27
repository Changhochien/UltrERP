import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

const createDowntimeMock = vi.hoisted(() => vi.fn());
const createOeeRecordMock = vi.hoisted(() => vi.fn());
const refreshMock = vi.hoisted(() => vi.fn());
const toastMock = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));

vi.mock("@/hooks/useToast", () => ({
	useToast: () => toastMock,
}));

vi.mock("../hooks/useBoms", () => ({
	useOeeDashboard: () => ({
		dashboard: {
			workstation_id: null,
			current_oee: 0.72,
			availability: 0.8,
			performance: 0.9,
			quality: 0.95,
			trend_data: [],
			downtime_pareto: [],
			period_start: "2026-04-01T00:00:00.000Z",
			period_end: "2026-04-30T00:00:00.000Z",
		},
		isLoading: false,
		isError: false,
		refresh: refreshMock,
	}),
	useWorkstations: () => ({
		workstations: [
			{
				id: "ws-1",
				code: "WS-001",
				name: "Assembly",
				status: "active",
				hourly_cost: "100",
				capacity: 1,
				disabled: false,
				created_at: "2026-04-01T00:00:00.000Z",
				updated_at: "2026-04-01T00:00:00.000Z",
			},
		],
	}),
	useWorkOrders: () => ({
		workOrders: [
			{
				id: "wo-1",
				code: "WO-001",
				name: "Assembly Run",
				product_id: "prod-1",
				bom_id: "bom-1",
				quantity: "20",
				produced_quantity: "0",
				status: "in_progress",
				transfer_mode: "direct_transfer",
				planned_start_date: null,
				due_date: null,
				created_at: "2026-04-01T00:00:00.000Z",
				updated_at: "2026-04-01T00:00:00.000Z",
			},
		],
	}),
	useDowntimeActions: () => ({
		createDowntime: createDowntimeMock,
	}),
	useOeeActions: () => ({
		createOeeRecord: createOeeRecordMock,
	}),
}));

afterEach(() => {
	cleanup();
	createDowntimeMock.mockReset();
	createOeeRecordMock.mockReset();
	refreshMock.mockReset();
	toastMock.success.mockReset();
	toastMock.error.mockReset();
	refreshMock.mockResolvedValue(undefined);
	createDowntimeMock.mockResolvedValue(undefined);
	createOeeRecordMock.mockResolvedValue(undefined);
});

describe("OeeDashboard", () => {
	it("submits downtime entries from the dashboard", async () => {
		const { OeeDashboard } = await import("./OeeDashboard");

		render(<OeeDashboard />);

		fireEvent.change(screen.getByLabelText("Downtime workstation"), {
			target: { value: "ws-1" },
		});
		fireEvent.change(screen.getByLabelText("Downtime work order"), {
			target: { value: "wo-1" },
		});
		fireEvent.change(screen.getByLabelText("Downtime notes"), {
			target: { value: "Unexpected stoppage" },
		});
		fireEvent.click(screen.getByRole("button", { name: "Log downtime" }));

		await waitFor(() => {
			expect(createDowntimeMock).toHaveBeenCalledWith(
				expect.objectContaining({
					workstation_id: "ws-1",
					work_order_id: "wo-1",
					reason: "unplanned_breakdown",
					remarks: "Unexpected stoppage",
				}),
			);
		});

		expect(refreshMock).toHaveBeenCalled();
		expect(toastMock.success).toHaveBeenCalled();
	});

	it("submits OEE records from the dashboard", async () => {
		const { OeeDashboard } = await import("./OeeDashboard");

		render(<OeeDashboard />);

		fireEvent.change(screen.getByLabelText("OEE workstation"), {
			target: { value: "ws-1" },
		});
		fireEvent.change(screen.getByLabelText("OEE work order"), {
			target: { value: "wo-1" },
		});
		fireEvent.change(screen.getByLabelText("Planned minutes"), {
			target: { value: "120" },
		});
		fireEvent.change(screen.getByLabelText("Stop minutes"), {
			target: { value: "15" },
		});
		fireEvent.change(screen.getByLabelText("Ideal cycle minutes"), {
			target: { value: "2" },
		});
		fireEvent.change(screen.getByLabelText("Total units"), {
			target: { value: "40" },
		});
		fireEvent.change(screen.getByLabelText("Good units"), {
			target: { value: "38" },
		});
		fireEvent.change(screen.getByLabelText("Rejected units"), {
			target: { value: "2" },
		});
		fireEvent.click(screen.getByRole("button", { name: "Record OEE" }));

		await waitFor(() => {
			expect(createOeeRecordMock).toHaveBeenCalledWith(
				expect.objectContaining({
					workstation_id: "ws-1",
					work_order_id: "wo-1",
					planned_production_time: 120,
					stop_time: 15,
					ideal_cycle_time: 2,
					total_count: 40,
					good_count: 38,
					reject_count: 2,
				}),
			);
		});

		expect(refreshMock).toHaveBeenCalled();
		expect(toastMock.success).toHaveBeenCalled();
	});
});