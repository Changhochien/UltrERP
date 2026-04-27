import { useParams } from "react-router-dom";

import { useWorkstation } from "@/domain/manufacturing/hooks/useBoms";

export function WorkstationDetailPage() {
	const { workstationId } = useParams<{ workstationId: string }>();
	const { workstation, isLoading, isError } = useWorkstation(workstationId ?? null);

	if (!workstationId) {
		return <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">Missing workstation identifier.</div>;
	}

	if (isLoading) {
		return <div className="rounded-md border border-gray-200 bg-white p-6 text-sm text-gray-500">Loading workstation...</div>;
	}

	if (isError || !workstation) {
		return <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">Failed to load workstation.</div>;
	}

	return (
		<div className="space-y-6">
			<div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
				<p className="text-sm font-medium uppercase tracking-wide text-gray-500">Workstation</p>
				<h1 className="mt-2 text-2xl font-semibold text-gray-900">{workstation.name}</h1>
				<p className="mt-1 text-sm text-gray-500">{workstation.code} · {workstation.status}</p>
				<div className="mt-6 grid gap-4 md:grid-cols-3">
					<div className="rounded-lg border border-gray-200 p-4"><p className="text-xs uppercase tracking-wide text-gray-500">Hourly Cost</p><p className="mt-2 text-lg font-semibold text-gray-900">{workstation.hourly_cost}</p></div>
					<div className="rounded-lg border border-gray-200 p-4"><p className="text-xs uppercase tracking-wide text-gray-500">Capacity</p><p className="mt-2 text-lg font-semibold text-gray-900">{workstation.capacity}</p></div>
					<div className="rounded-lg border border-gray-200 p-4"><p className="text-xs uppercase tracking-wide text-gray-500">Availability</p><p className="mt-2 text-lg font-semibold text-gray-900">{workstation.disabled ? "Disabled" : "Available"}</p></div>
				</div>
			</div>

			<div className="rounded-xl border border-gray-200 bg-white shadow-sm">
				<div className="border-b border-gray-200 px-6 py-4">
					<h2 className="text-lg font-semibold text-gray-900">Working Hours</h2>
				</div>
				<div className="overflow-x-auto">
					<table className="min-w-full divide-y divide-gray-200">
						<thead className="bg-gray-50">
							<tr>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Day</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Start</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">End</th>
							</tr>
						</thead>
						<tbody className="divide-y divide-gray-200">
							{workstation.hours.length === 0 ? (
								<tr>
									<td colSpan={3} className="px-6 py-4 text-sm text-gray-500">No working hours configured.</td>
								</tr>
							) : (
								workstation.hours.map((hour) => (
									<tr key={`${hour.day_of_week}-${hour.start_time}-${hour.end_time}`}>
										<td className="px-6 py-4 text-sm text-gray-700">{hour.day_of_week}</td>
										<td className="px-6 py-4 text-sm text-gray-700">{hour.start_time}</td>
										<td className="px-6 py-4 text-sm text-gray-700">{hour.end_time}</td>
									</tr>
								))
							)}
						</tbody>
					</table>
				</div>
			</div>
		</div>
	);
}