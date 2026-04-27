import { useState } from "react";
import { useParams } from "react-router-dom";

import { useProductionPlan, useProductionPlanActions } from "@/domain/manufacturing/hooks/useBoms";

function getShortageCount(summary: Record<string, unknown> | null): number {
	if (!summary) return 0;
	const itemCount = summary.item_count;
	if (typeof itemCount === "number") return itemCount;
	const items = summary.items;
	return Array.isArray(items) ? items.length : 0;
}

function getCapacityText(summary: Record<string, unknown> | null): string {
	if (!summary) return "-";
	const totalHours = summary.total_hours;
	const totalCost = summary.total_cost;
	if (typeof totalHours === "number" && typeof totalCost === "string") {
		return `${totalHours.toFixed(2)} h · ${totalCost}`;
	}
	return "-";
}

export function ProductionPlanDetailPage() {
	const { planId } = useParams<{ planId: string }>();
	const { plan, isLoading, isError, refresh } = useProductionPlan(planId ?? null);
	const { firmProductionPlan } = useProductionPlanActions();
	const [isFirming, setIsFirming] = useState(false);

	if (!planId) {
		return <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">Missing production-plan identifier.</div>;
	}

	if (isLoading) {
		return <div className="rounded-md border border-gray-200 bg-white p-6 text-sm text-gray-500">Loading production plan...</div>;
	}

	if (isError || !plan) {
		return <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">Failed to load production plan.</div>;
	}

	const handleFirm = async () => {
		setIsFirming(true);
		try {
			await firmProductionPlan(plan.id);
			await refresh();
		} catch (error) {
			window.alert(error instanceof Error ? error.message : "Failed to firm production plan");
		} finally {
			setIsFirming(false);
		}
	};

	return (
		<div className="space-y-6">
			<div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
				<div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
					<div>
						<p className="text-sm font-medium uppercase tracking-wide text-gray-500">Production Plan</p>
						<h1 className="text-2xl font-semibold text-gray-900">{plan.name}</h1>
						<p className="text-sm text-gray-500">{plan.code} · {plan.planning_strategy}</p>
					</div>
					<div className="flex items-center gap-3">
						<span className="rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-700">{plan.status}</span>
						{["draft", "reviewed"].includes(plan.status) && (
							<button onClick={handleFirm} disabled={isFirming} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
								{isFirming ? "Firming..." : "Firm Production Plan"}
							</button>
						)}
					</div>
				</div>
			</div>

			<div className="rounded-xl border border-gray-200 bg-white shadow-sm">
				<div className="border-b border-gray-200 px-6 py-4">
					<h2 className="text-lg font-semibold text-gray-900">Plan Lines</h2>
				</div>
				<div className="overflow-x-auto">
					<table className="min-w-full divide-y divide-gray-200">
						<thead className="bg-gray-50">
							<tr>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Product</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Sales Demand</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Forecast</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Total Demand</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Available</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Open WO</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Proposed</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Shortages</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Capacity</th>
							</tr>
						</thead>
						<tbody className="divide-y divide-gray-200">
							{plan.lines.map((line) => (
								<tr key={line.id}>
									<td className="px-6 py-4 text-sm text-gray-900">{line.product_id}</td>
									<td className="px-6 py-4 text-sm text-gray-700">{line.sales_order_demand}</td>
									<td className="px-6 py-4 text-sm text-gray-700">{line.forecast_demand}</td>
									<td className="px-6 py-4 text-sm font-medium text-gray-900">{line.total_demand}</td>
									<td className="px-6 py-4 text-sm text-gray-700">{line.available_stock}</td>
									<td className="px-6 py-4 text-sm text-gray-700">{line.open_work_order_qty}</td>
									<td className="px-6 py-4 text-sm font-medium text-gray-900">{line.proposed_qty}</td>
									<td className="px-6 py-4 text-sm text-gray-700">{getShortageCount(line.shortage_summary)}</td>
									<td className="px-6 py-4 text-sm text-gray-700">{getCapacityText(line.capacity_summary)}</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			</div>
		</div>
	);
}