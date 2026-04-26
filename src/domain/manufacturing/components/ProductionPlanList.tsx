/** Production Plan List Component - Production plans management. */

import { useState } from "react";
import { useProductionPlans } from "../hooks/useBoms";
import type { ProductionPlanStatus } from "../types";

interface ProductionPlanListProps {
	showCreateButton?: boolean;
}

const STATUS_LABELS: Record<ProductionPlanStatus, string> = {
	draft: "Draft",
	reviewed: "Reviewed",
	firmed: "Firmed",
	closed: "Closed",
};

const STATUS_COLORS: Record<ProductionPlanStatus, string> = {
	draft: "bg-gray-100 text-gray-800",
	reviewed: "bg-blue-100 text-blue-800",
	firmed: "bg-green-100 text-green-800",
	closed: "bg-purple-100 text-purple-800",
};

export function ProductionPlanList({ showCreateButton = true }: ProductionPlanListProps) {
	const [status, setStatus] = useState<string | undefined>(undefined);
	const [page, setPage] = useState(1);
	const pageSize = 20;

	const { plans, total, isLoading, isError } = useProductionPlans({
		status,
		page,
		page_size: pageSize,
	});

	const totalPages = Math.ceil(total / pageSize);

	if (isError) {
		return (
			<div className="rounded-md bg-red-50 p-4">
				<p className="text-sm text-red-700">Failed to load production plans</p>
			</div>
		);
	}

	return (
		<div className="space-y-4">
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-4">
					<select
						value={status ?? ""}
						onChange={(e) => {
							setStatus(e.target.value || undefined);
							setPage(1);
						}}
						className="rounded-md border border-gray-300 px-3 py-2 text-sm"
					>
						<option value="">All Status</option>
						<option value="draft">Draft</option>
						<option value="reviewed">Reviewed</option>
						<option value="firmed">Firmed</option>
						<option value="closed">Closed</option>
					</select>
				</div>
				{showCreateButton && (
					<button
						onClick={() => window.location.href = "/manufacturing/production-plans/create"}
						className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
					>
						Create Production Plan
					</button>
				)}
			</div>

			<div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
				<table className="min-w-full divide-y divide-gray-200">
					<thead className="bg-gray-50">
						<tr>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Code</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Name</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Status</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Period</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Lines</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Created</th>
						</tr>
					</thead>
					<tbody className="divide-y divide-gray-200">
						{isLoading ? (
							<tr>
								<td colSpan={6} className="px-4 py-8 text-center text-gray-500">
									Loading...
								</td>
							</tr>
						) : plans.length === 0 ? (
							<tr>
								<td colSpan={6} className="px-4 py-8 text-center text-gray-500">
									No production plans found
								</td>
							</tr>
						) : (
							plans.map((plan) => (
								<tr
									key={plan.id}
									className="cursor-pointer hover:bg-gray-50"
									onClick={() => window.location.href = `/manufacturing/production-plans/${plan.id}`}
								>
									<td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
										{plan.code}
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										{plan.name}
									</td>
									<td className="whitespace-nowrap px-4 py-3">
										<span
											className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${STATUS_COLORS[plan.status]}`}
										>
											{STATUS_LABELS[plan.status]}
										</span>
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										{new Date(plan.start_date).toLocaleDateString()} - {new Date(plan.end_date).toLocaleDateString()}
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										{plan.line_count}
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										{new Date(plan.created_at).toLocaleDateString()}
									</td>
								</tr>
							))
						)}
					</tbody>
				</table>
			</div>

			{totalPages > 1 && (
				<div className="flex items-center justify-between">
					<p className="text-sm text-gray-500">
						Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} results
					</p>
					<div className="flex gap-2">
						<button
							onClick={() => setPage((p) => Math.max(1, p - 1))}
							disabled={page === 1}
							className="rounded-md border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
						>
							Previous
						</button>
						<button
							onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
							disabled={page === totalPages}
							className="rounded-md border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
						>
							Next
						</button>
					</div>
				</div>
			)}
		</div>
	);
}
