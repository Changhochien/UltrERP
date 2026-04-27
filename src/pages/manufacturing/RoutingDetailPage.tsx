import { useState } from "react";
import { useParams } from "react-router-dom";

import { useRouting, useRoutingActions } from "@/domain/manufacturing/hooks/useBoms";
import type { RoutingCalculationResult } from "@/domain/manufacturing/types";

export function RoutingDetailPage() {
	const { routingId } = useParams<{ routingId: string }>();
	const { routing, isLoading, isError } = useRouting(routingId ?? null);
	const { calculateRouting } = useRoutingActions();
	const [quantity, setQuantity] = useState("1");
	const [calculation, setCalculation] = useState<RoutingCalculationResult | null>(null);
	const [isCalculating, setIsCalculating] = useState(false);

	if (!routingId) {
		return <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">Missing routing identifier.</div>;
	}

	if (isLoading) {
		return <div className="rounded-md border border-gray-200 bg-white p-6 text-sm text-gray-500">Loading routing...</div>;
	}

	if (isError || !routing) {
		return <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">Failed to load routing.</div>;
	}

	const handleCalculate = async () => {
		setIsCalculating(true);
		try {
			setCalculation(await calculateRouting(routing.id, Number(quantity)));
		} catch (error) {
			window.alert(error instanceof Error ? error.message : "Failed to calculate routing");
		} finally {
			setIsCalculating(false);
		}
	};

	return (
		<div className="space-y-6">
			<div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
				<div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
					<div>
						<p className="text-sm font-medium uppercase tracking-wide text-gray-500">Routing</p>
						<h1 className="text-2xl font-semibold text-gray-900">{routing.name}</h1>
						<p className="text-sm text-gray-500">{routing.code} · {routing.status}</p>
					</div>
					<div className="flex items-end gap-3">
						<label className="flex flex-col gap-2 text-sm text-gray-600">
							Quantity
							<input value={quantity} onChange={(event) => setQuantity(event.target.value)} className="rounded-md border border-gray-300 px-3 py-2" />
						</label>
						<button onClick={handleCalculate} disabled={isCalculating} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
							{isCalculating ? "Calculating..." : "Calculate Plan"}
						</button>
					</div>
				</div>

				{calculation && (
					<div className="mt-6 grid gap-4 md:grid-cols-4">
						<div className="rounded-lg border border-gray-200 p-4"><p className="text-xs uppercase tracking-wide text-gray-500">Total Minutes</p><p className="mt-2 text-lg font-semibold text-gray-900">{calculation.total_minutes}</p></div>
						<div className="rounded-lg border border-gray-200 p-4"><p className="text-xs uppercase tracking-wide text-gray-500">Total Hours</p><p className="mt-2 text-lg font-semibold text-gray-900">{calculation.total_hours.toFixed(2)}</p></div>
						<div className="rounded-lg border border-gray-200 p-4"><p className="text-xs uppercase tracking-wide text-gray-500">Estimated Cost</p><p className="mt-2 text-lg font-semibold text-gray-900">{calculation.total_cost}</p></div>
						<div className="rounded-lg border border-gray-200 p-4"><p className="text-xs uppercase tracking-wide text-gray-500">Operations</p><p className="mt-2 text-lg font-semibold text-gray-900">{calculation.operation_count}</p></div>
					</div>
				)}
			</div>

			<div className="rounded-xl border border-gray-200 bg-white shadow-sm">
				<div className="border-b border-gray-200 px-6 py-4">
					<h2 className="text-lg font-semibold text-gray-900">Operations</h2>
				</div>
				<div className="overflow-x-auto">
					<table className="min-w-full divide-y divide-gray-200">
						<thead className="bg-gray-50">
							<tr>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Sequence</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Operation</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Workstation</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Setup</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Fixed</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Variable / Unit</th>
							</tr>
						</thead>
						<tbody className="divide-y divide-gray-200">
							{routing.operations.map((operation) => (
								<tr key={operation.id}>
									<td className="px-6 py-4 text-sm text-gray-700">{operation.sequence}</td>
									<td className="px-6 py-4 text-sm font-medium text-gray-900">{operation.operation_name}</td>
									<td className="px-6 py-4 text-sm text-gray-700">{operation.workstation_id || "-"}</td>
									<td className="px-6 py-4 text-sm text-gray-700">{operation.setup_minutes} min</td>
									<td className="px-6 py-4 text-sm text-gray-700">{operation.fixed_run_minutes} min</td>
									<td className="px-6 py-4 text-sm text-gray-700">{operation.variable_run_minutes_per_unit}</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			</div>
		</div>
	);
}