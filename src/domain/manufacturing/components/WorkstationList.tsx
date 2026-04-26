/** Workstation List Component - Manufacturing workstations list. */

import { useState } from "react";
import { useWorkstations } from "../hooks/useBoms";

interface WorkstationListProps {
	showCreateButton?: boolean;
}

const STATUS_COLORS = {
	active: "bg-green-100 text-green-800",
	disabled: "bg-gray-100 text-gray-800",
};

export function WorkstationList({ showCreateButton = true }: WorkstationListProps) {
	const [status, setStatus] = useState<string | undefined>(undefined);
	const [page, setPage] = useState(1);
	const pageSize = 20;

	const { workstations, total, isLoading, isError } = useWorkstations({
		status,
		page,
		page_size: pageSize,
	});

	const totalPages = Math.ceil(total / pageSize);

	if (isError) {
		return (
			<div className="rounded-md bg-red-50 p-4">
				<p className="text-sm text-red-700">Failed to load workstations</p>
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
						<option value="active">Active</option>
						<option value="disabled">Disabled</option>
					</select>
				</div>
				{showCreateButton && (
					<button
						onClick={() => window.location.href = "/manufacturing/workstations/create"}
						className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
					>
						Create Workstation
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
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Hourly Cost</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Capacity</th>
						</tr>
					</thead>
					<tbody className="divide-y divide-gray-200">
						{isLoading ? (
							<tr>
								<td colSpan={5} className="px-4 py-8 text-center text-gray-500">
									Loading...
								</td>
							</tr>
						) : workstations.length === 0 ? (
							<tr>
								<td colSpan={5} className="px-4 py-8 text-center text-gray-500">
									No workstations found
								</td>
							</tr>
						) : (
							workstations.map((ws) => (
								<tr
									key={ws.id}
									className="cursor-pointer hover:bg-gray-50"
									onClick={() => window.location.href = `/manufacturing/workstations/${ws.id}`}
								>
									<td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
										{ws.code}
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										{ws.name}
									</td>
									<td className="whitespace-nowrap px-4 py-3">
										<span
											className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${STATUS_COLORS[ws.status]}`}
										>
											{ws.status}
										</span>
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										${ws.hourly_cost}
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										{ws.capacity}
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
