/** Routing List Component - Manufacturing routing templates list. */

import { useState } from "react";
import { useRoutings } from "../hooks/useBoms";

interface RoutingListProps {
	showCreateButton?: boolean;
}

const STATUS_COLORS = {
	draft: "bg-gray-100 text-gray-800",
	submitted: "bg-green-100 text-green-800",
	inactive: "bg-yellow-100 text-yellow-800",
};

export function RoutingList({ showCreateButton = true }: RoutingListProps) {
	const [status, setStatus] = useState<string | undefined>(undefined);
	const [page, setPage] = useState(1);
	const pageSize = 20;

	const { routings, total, isLoading, isError } = useRoutings({
		status,
		page,
		page_size: pageSize,
	});

	const totalPages = Math.ceil(total / pageSize);

	if (isError) {
		return (
			<div className="rounded-md bg-red-50 p-4">
				<p className="text-sm text-red-700">Failed to load routings</p>
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
						<option value="inactive">Inactive</option>
					</select>
				</div>
				{showCreateButton && (
					<button
						onClick={() => window.location.href = "/manufacturing/routings/create"}
						className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
					>
						Create Routing
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
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Operations</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Created</th>
						</tr>
					</thead>
					<tbody className="divide-y divide-gray-200">
						{isLoading ? (
							<tr>
								<td colSpan={5} className="px-4 py-8 text-center text-gray-500">
									Loading...
								</td>
							</tr>
						) : routings.length === 0 ? (
							<tr>
								<td colSpan={5} className="px-4 py-8 text-center text-gray-500">
									No routings found
								</td>
							</tr>
						) : (
							routings.map((routing) => (
								<tr
									key={routing.id}
									className="cursor-pointer hover:bg-gray-50"
									onClick={() => window.location.href = `/manufacturing/routings/${routing.id}`}
								>
									<td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
										{routing.code}
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										{routing.name}
									</td>
									<td className="whitespace-nowrap px-4 py-3">
										<span
											className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${STATUS_COLORS[routing.status]}`}
										>
											{routing.status}
										</span>
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										{routing.operation_count}
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										{new Date(routing.created_at).toLocaleDateString()}
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
