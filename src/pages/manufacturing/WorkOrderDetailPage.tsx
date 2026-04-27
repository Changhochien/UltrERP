import { useState } from "react";
import { useParams } from "react-router-dom";

import { useWorkOrder, useWorkOrderActions } from "@/domain/manufacturing/hooks/useBoms";
import type { WorkOrderStatus } from "@/domain/manufacturing/types";

const STATUS_COLORS: Record<WorkOrderStatus, string> = {
	draft: "bg-gray-100 text-gray-800",
	submitted: "bg-blue-100 text-blue-800",
	not_started: "bg-yellow-100 text-yellow-800",
	in_progress: "bg-indigo-100 text-indigo-800",
	completed: "bg-green-100 text-green-800",
	stopped: "bg-orange-100 text-orange-800",
	cancelled: "bg-red-100 text-red-800",
};

export function WorkOrderDetailPage() {
	const { workOrderId } = useParams<{ workOrderId: string }>();
	const { workOrder, isLoading, isError, refresh } = useWorkOrder(workOrderId ?? null);
	const { transitionWorkOrder, reserveMaterials, transferMaterials, completeWorkOrder } = useWorkOrderActions();
	const [busyAction, setBusyAction] = useState<string | null>(null);

	if (!workOrderId) {
		return <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">Missing work-order identifier.</div>;
	}

	if (isLoading) {
		return <div className="rounded-md border border-gray-200 bg-white p-6 text-sm text-gray-500">Loading work order...</div>;
	}

	if (isError || !workOrder) {
		return <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">Failed to load work order.</div>;
	}

	const runAction = async (label: string, action: () => Promise<unknown>) => {
		setBusyAction(label);
		try {
			await action();
			await refresh();
		} catch (error) {
			window.alert(error instanceof Error ? error.message : `Failed to ${label.toLowerCase()}`);
		} finally {
			setBusyAction(null);
		}
	};

	const handleTransition = async (status: WorkOrderStatus) => {
		let reason: string | undefined;
		if (status === "stopped" || status === "cancelled") {
			reason = window.prompt(`Enter a reason for marking this work order as ${status}:`) || undefined;
			if (!reason) {
				return;
			}
		}
		await runAction(`Set ${status}`, async () => {
			await transitionWorkOrder(workOrder.id, { status, reason });
		});
	};

	const handleComplete = async () => {
		const producedQuantity = window.prompt("Enter produced quantity", workOrder.quantity);
		if (!producedQuantity) {
			return;
		}
		await runAction("Complete", async () => {
			await completeWorkOrder(workOrder.id, { produced_quantity: producedQuantity });
		});
	};

	return (
		<div className="space-y-6">
			<div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
				<div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
					<div className="space-y-2">
						<p className="text-sm font-medium uppercase tracking-wide text-gray-500">Work Order</p>
						<h1 className="text-2xl font-semibold text-gray-900">{workOrder.name}</h1>
						<p className="text-sm text-gray-500">{workOrder.code} · Product {workOrder.product_id}</p>
					</div>
					<span className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ${STATUS_COLORS[workOrder.status]}`}>
						{workOrder.status}
					</span>
				</div>

				<div className="mt-6 grid gap-4 md:grid-cols-4">
					<div className="rounded-lg border border-gray-200 p-4">
						<p className="text-xs uppercase tracking-wide text-gray-500">Planned Quantity</p>
						<p className="mt-2 text-lg font-semibold text-gray-900">{workOrder.quantity}</p>
					</div>
					<div className="rounded-lg border border-gray-200 p-4">
						<p className="text-xs uppercase tracking-wide text-gray-500">Produced Quantity</p>
						<p className="mt-2 text-lg font-semibold text-gray-900">{workOrder.produced_quantity}</p>
					</div>
					<div className="rounded-lg border border-gray-200 p-4">
						<p className="text-xs uppercase tracking-wide text-gray-500">Transfer Mode</p>
						<p className="mt-2 text-lg font-semibold text-gray-900">{workOrder.transfer_mode}</p>
					</div>
					<div className="rounded-lg border border-gray-200 p-4">
						<p className="text-xs uppercase tracking-wide text-gray-500">Due Date</p>
						<p className="mt-2 text-lg font-semibold text-gray-900">{workOrder.due_date ? new Date(workOrder.due_date).toLocaleDateString() : "-"}</p>
					</div>
				</div>

				<div className="mt-6 flex flex-wrap gap-3">
					{workOrder.status === "draft" && (
						<button onClick={() => handleTransition("submitted")} disabled={busyAction !== null} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
							Submit Work Order
						</button>
					)}
					{workOrder.status === "submitted" && (
						<button onClick={() => handleTransition("not_started")} disabled={busyAction !== null} className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
							Mark Not Started
						</button>
					)}
					{workOrder.status === "not_started" && (
						<button onClick={() => handleTransition("in_progress")} disabled={busyAction !== null} className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
							Start Production
						</button>
					)}
					{["submitted", "not_started", "in_progress"].includes(workOrder.status) && (
						<button onClick={() => runAction("Reserve Materials", async () => reserveMaterials(workOrder.id, { action: "reserve" }))} disabled={busyAction !== null} className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50">
							Reserve Materials
						</button>
					)}
					{workOrder.status === "in_progress" && (
						<>
							<button onClick={() => runAction("Transfer Materials", async () => transferMaterials(workOrder.id, {}))} disabled={busyAction !== null} className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50">
								Transfer Materials
							</button>
							<button onClick={handleComplete} disabled={busyAction !== null} className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50">
								Complete Work Order
							</button>
						</>
					)}
					{!["completed", "cancelled"].includes(workOrder.status) && (
						<>
							<button onClick={() => handleTransition("stopped")} disabled={busyAction !== null} className="rounded-md border border-orange-300 px-4 py-2 text-sm font-medium text-orange-700 hover:bg-orange-50 disabled:opacity-50">
								Stop
							</button>
							<button onClick={() => handleTransition("cancelled")} disabled={busyAction !== null} className="rounded-md border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50">
								Cancel
							</button>
						</>
					)}
				</div>
			</div>

			<div className="rounded-xl border border-gray-200 bg-white shadow-sm">
				<div className="border-b border-gray-200 px-6 py-4">
					<h2 className="text-lg font-semibold text-gray-900">Material Execution</h2>
				</div>
				<div className="overflow-x-auto">
					<table className="min-w-full divide-y divide-gray-200">
						<thead className="bg-gray-50">
							<tr>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Item</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Required</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Reserved</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Transferred</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Consumed</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Source Warehouse</th>
							</tr>
						</thead>
						<tbody className="divide-y divide-gray-200">
							{workOrder.material_lines.map((line) => (
								<tr key={line.id}>
									<td className="px-6 py-4 text-sm text-gray-900">{line.item_name}<div className="text-xs text-gray-500">{line.item_code}</div></td>
									<td className="px-6 py-4 text-sm text-gray-700">{line.required_quantity}</td>
									<td className="px-6 py-4 text-sm text-gray-700">{line.reserved_quantity}</td>
									<td className="px-6 py-4 text-sm text-gray-700">{line.transferred_quantity}</td>
									<td className="px-6 py-4 text-sm text-gray-700">{line.consumed_quantity}</td>
									<td className="px-6 py-4 text-sm text-gray-700">{line.source_warehouse_id || "-"}</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			</div>
		</div>
	);
}