import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

const createBomMock = vi.hoisted(() => vi.fn());
const createWorkstationMock = vi.hoisted(() => vi.fn());
const createRoutingMock = vi.hoisted(() => vi.fn());
const createProductionPlanMock = vi.hoisted(() => vi.fn());

vi.mock("../hooks/useBoms", () => ({
	useBomActions: () => ({
		createBom: createBomMock,
	}),
	useWorkstationActions: () => ({
		createWorkstation: createWorkstationMock,
	}),
	useRoutingActions: () => ({
		createRouting: createRoutingMock,
	}),
	useProductionPlanActions: () => ({
		createProductionPlan: createProductionPlanMock,
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
}));

afterEach(() => {
	cleanup();
	createBomMock.mockReset();
	createWorkstationMock.mockReset();
	createRoutingMock.mockReset();
	createProductionPlanMock.mockReset();
	createBomMock.mockResolvedValue(undefined);
	createWorkstationMock.mockResolvedValue(undefined);
	createRoutingMock.mockResolvedValue(undefined);
	createProductionPlanMock.mockResolvedValue(undefined);
});

describe("manufacturing authoring forms", () => {
	it("submits BOM authoring payloads", async () => {
		const { BomForm } = await import("./BomForm");

		render(<BomForm />);

		fireEvent.change(screen.getByLabelText("Product ID"), { target: { value: "prod-1" } });
		fireEvent.change(screen.getByLabelText("Item ID"), { target: { value: "item-1" } });
		fireEvent.change(screen.getByLabelText("Item Code"), { target: { value: "RM-001" } });
		fireEvent.change(screen.getByLabelText("Item Name"), { target: { value: "Raw Material" } });
		fireEvent.click(screen.getByRole("button", { name: "Create BOM" }));

		await waitFor(() => {
			expect(createBomMock).toHaveBeenCalledWith(
				expect.objectContaining({
					product_id: "prod-1",
					bom_quantity: "1",
					items: [
						expect.objectContaining({
							item_id: "item-1",
							item_code: "RM-001",
							item_name: "Raw Material",
							required_quantity: "1",
							idx: 0,
						}),
					],
				}),
			);
		});
	});

	it("submits workstation authoring payloads", async () => {
		const { WorkstationForm } = await import("./WorkstationForm");

		render(<WorkstationForm />);

		fireEvent.change(screen.getByLabelText("Code"), { target: { value: "WS-NEW" } });
		fireEvent.change(screen.getByLabelText("Name"), { target: { value: "New Workstation" } });
		fireEvent.click(screen.getByRole("button", { name: "Create Workstation" }));

		await waitFor(() => {
			expect(createWorkstationMock).toHaveBeenCalledWith(
				expect.objectContaining({
					code: "WS-NEW",
					name: "New Workstation",
					capacity: 1,
					hours: [
						expect.objectContaining({
							day_of_week: 1,
							start_time: "09:00",
							end_time: "17:00",
						}),
					],
				}),
			);
		});
	});

	it("submits routing authoring payloads", async () => {
		const { RoutingForm } = await import("./RoutingForm");

		render(<RoutingForm />);

		fireEvent.change(screen.getByLabelText("Code"), { target: { value: "RT-001" } });
		fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Assembly Route" } });
		fireEvent.change(screen.getByLabelText("Operation Name"), { target: { value: "Assembly" } });
		fireEvent.change(screen.getByLabelText("Workstation"), { target: { value: "ws-1" } });
		fireEvent.click(screen.getByRole("button", { name: "Create Routing" }));

		await waitFor(() => {
			expect(createRoutingMock).toHaveBeenCalledWith(
				expect.objectContaining({
					code: "RT-001",
					name: "Assembly Route",
					operations: [
						expect.objectContaining({
							operation_name: "Assembly",
							workstation_id: "ws-1",
							sequence: 1,
							idx: 0,
						}),
					],
				}),
			);
		});
	});

	it("submits production-plan authoring payloads", async () => {
		const { ProductionPlanForm } = await import("./ProductionPlanForm");

		render(<ProductionPlanForm />);

		fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Weekly Plan" } });
		fireEvent.change(screen.getByLabelText("Product ID"), { target: { value: "prod-1" } });
		fireEvent.change(screen.getByLabelText("Proposed Quantity"), { target: { value: "12" } });
		fireEvent.click(screen.getByRole("button", { name: "Create Production Plan" }));

		await waitFor(() => {
			expect(createProductionPlanMock).toHaveBeenCalledWith(
				expect.objectContaining({
					name: "Weekly Plan",
					planning_strategy: "make_to_order",
					start_date: expect.any(String),
					end_date: expect.any(String),
					lines: [
						expect.objectContaining({
							product_id: "prod-1",
							proposed_qty: "12",
							idx: 0,
						}),
					],
				}),
			);
		});
	});
});