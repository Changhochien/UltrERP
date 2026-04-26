/** Work Order List Component - Manufacturing work orders list with filters. */

import { useState } from "react";
import { useWorkOrders } from "../hooks/useBoms";
import type { WorkOrderStatus } from "../types";

interface WorkOrderListProps {
	showCreateButton?: boolean;
}

const STATUS_LABELS: Record<WorkOrderStatus, string> = {
	draft: "Draft",
	submitted: "Submitted",
	not_started: "Not Started",
	in_progress: "In Progress",
	completed: "Completed",
	stopped: "Stopped",
	cancelled: "Cancelled",
};

const STATUS_COLORS: Record<WorkOrderStatus, string> = {
	draft: "bg-gray-100 text-gray-800",
	submitted: "bg-blue-100 text-blue-800",
	not_started: "bg-yellow-100 text-yellow-800",
	in_progress: "bg-indigo-100 text-indigo-800",
	completed: "bg-green-100 text-green-800",
	stopped: "bg-orange-100 text-orange-800",
	cancelled: "bg-red-100 text-red-800",
};

export function WorkOrderList({ showCreateButton = true }: WorkOrderListProps) {
	const [status, setStatus] = useState<string | undefined>(undefined);
	const [page, setPage] = useState(1);
	const pageSize = 20;

	const { workOrders, total, isLoading, isError } = useWorkOrders({
		status,
		page,
		page_size: pageSize,
	});

	const totalPages = Math.ceil(total / pageSize);

	if (isError) {
		return (
			<div className="rounded-md bg-red-50 p-4">
				<p className="text-sm text-red-700">Failed to load work orders</p>
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
						<option value="submitted">Submitted</option>
						<option value="not_started">Not Started</option>
						<option value="in_progress">In Progress</option>
						<option value="completed">Completed</option>
						<option value="stopped">Stopped</option>
						<option value="cancelled">Cancelled</option>
					</select>
				</div>
				{showCreateButton && (
					<button
						onClick={() => window.location.href = "/manufacturing/work-orders/create"}
						className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
					>
						Create Work Order
					</button>
				)}
			</div>

			<div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
				<table className="min-w-full divide-y divide-gray-200">
					<thead className="bg-gray-50">
						<tr>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Code</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Product</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Qty</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Status</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Due Date</th>
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
						) : workOrders.length === 0 ? (
							<tr>
								<td colSpan={6} className="px-4 py-8 text-center text-gray-500">
									No work orders found
								</td>
							</tr>
						) : (
							workOrders.map((wo) => (
								<tr
									key={wo.id}
									className="cursor-pointer hover:bg-gray-50"
									onClick={() => window.location.href = `/manufacturing/work-orders/${wo.id}`}
								>
									<td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
										{wo.code}
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										{wo.product_id}
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										{wo.quantity}
									</td>
									<td className="whitespace-nowrap px-4 py-3">
										<span
											className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${STATUS_COLORS[wo.status]}`}
										>
											{STATUS_LABELS[wo.status]}
										</span>
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										{wo.due_date ? new Date(wo.due_date).toLocaleDateString() : "-"}
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										{new Date(wo.created_at).toLocaleDateString()}
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
