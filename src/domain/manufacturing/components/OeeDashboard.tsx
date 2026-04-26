/** OEE Dashboard Component - Equipment effectiveness dashboard. */

import { useState } from "react";
import { useOeeDashboard } from "../hooks/useBoms";

export function OeeDashboard() {
	const [workstationId, setWorkstationId] = useState<string | undefined>(undefined);
	const [startDate, setStartDate] = useState<string>(
		new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
	);
	const [endDate, setEndDate] = useState<string>(new Date().toISOString().split("T")[0]);

	const { dashboard, isLoading, isError } = useOeeDashboard({
		workstation_id: workstationId,
		start_date: startDate,
		end_date: endDate,
	});

	if (isError) {
		return (
			<div className="rounded-md bg-red-50 p-4">
				<p className="text-sm text-red-700">Failed to load OEE data</p>
			</div>
		);
	}

	const formatPercentage = (value: number) => `${(value * 100).toFixed(1)}%`;

	return (
		<div className="space-y-6">
			<div className="flex items-center gap-4">
				<div>
					<label className="block text-xs text-gray-500">Workstation</label>
					<input
						type="text"
						placeholder="All workstations"
						value={workstationId ?? ""}
						onChange={(e) => setWorkstationId(e.target.value || undefined)}
						className="rounded-md border border-gray-300 px-3 py-2 text-sm"
					/>
				</div>
				<div>
					<label className="block text-xs text-gray-500">From</label>
					<input
						type="date"
						value={startDate}
						onChange={(e) => setStartDate(e.target.value)}
						className="rounded-md border border-gray-300 px-3 py-2 text-sm"
					/>
				</div>
				<div>
					<label className="block text-xs text-gray-500">To</label>
					<input
						type="date"
						value={endDate}
						onChange={(e) => setEndDate(e.target.value)}
						className="rounded-md border border-gray-300 px-3 py-2 text-sm"
					/>
				</div>
			</div>

			{isLoading ? (
				<div className="flex items-center justify-center py-12">
					<p className="text-gray-500">Loading...</p>
				</div>
			) : dashboard ? (
				<>
					{/* OEE KPI Cards */}
					<div className="grid grid-cols-1 gap-6 md:grid-cols-4">
						<div className="rounded-lg border border-gray-200 bg-white p-6">
							<h3 className="text-sm font-medium text-gray-500">OEE</h3>
							<p className="mt-2 text-3xl font-bold text-gray-900">
								{formatPercentage(dashboard.current_oee)}
							</p>
							<p className="mt-1 text-xs text-gray-500">
								Overall Equipment Effectiveness
							</p>
						</div>
						<div className="rounded-lg border border-gray-200 bg-white p-6">
							<h3 className="text-sm font-medium text-gray-500">Availability</h3>
							<p className="mt-2 text-3xl font-bold text-green-600">
								{formatPercentage(dashboard.availability)}
							</p>
							<p className="mt-1 text-xs text-gray-500">Run time / Planned time</p>
						</div>
						<div className="rounded-lg border border-gray-200 bg-white p-6">
							<h3 className="text-sm font-medium text-gray-500">Performance</h3>
							<p className="mt-2 text-3xl font-bold text-blue-600">
								{formatPercentage(dashboard.performance)}
							</p>
							<p className="mt-1 text-xs text-gray-500">Ideal cycle / Run time</p>
						</div>
						<div className="rounded-lg border border-gray-200 bg-white p-6">
							<h3 className="text-sm font-medium text-gray-500">Quality</h3>
							<p className="mt-2 text-3xl font-bold text-purple-600">
								{formatPercentage(dashboard.quality)}
							</p>
							<p className="mt-1 text-xs text-gray-500">Good count / Total count</p>
						</div>
					</div>

					{/* Downtime Pareto */}
					<div className="rounded-lg border border-gray-200 bg-white p-6">
						<h2 className="mb-4 text-lg font-medium text-gray-900">Downtime Pareto</h2>
						{dashboard.downtime_pareto.length === 0 ? (
							<p className="text-center text-gray-500 py-8">No downtime data available</p>
						) : (
							<div className="space-y-2">
								{dashboard.downtime_pareto.map((item, index) => (
									<div key={item.reason} className="flex items-center gap-4">
										<div className="w-8 text-center font-medium text-gray-500">{index + 1}</div>
										<div className="flex-1">
											<div className="flex items-center justify-between text-sm">
												<span className="font-medium text-gray-700">
													{item.reason.replace(/_/g, " ")}
												</span>
												<span className="text-gray-500">
													{item.frequency} events | {item.total_duration_minutes} min | {item.percentage}%
												</span>
											</div>
											<div className="mt-1 h-2 w-full rounded-full bg-gray-200">
												<div
													className="h-2 rounded-full bg-red-500"
													style={{ width: `${item.percentage}%` }}
												/>
											</div>
										</div>
									</div>
								))}
							</div>
						)}
					</div>

					{/* OEE Trend */}
					<div className="rounded-lg border border-gray-200 bg-white p-6">
						<h2 className="mb-4 text-lg font-medium text-gray-900">OEE Trend</h2>
						{dashboard.trend_data.length === 0 ? (
							<p className="text-center text-gray-500 py-8">No OEE records available</p>
						) : (
							<div className="space-y-2">
								{dashboard.trend_data.slice(0, 10).map((record) => (
									<div
										key={record.id}
										className="flex items-center justify-between rounded border border-gray-100 px-4 py-2"
									>
										<span className="text-sm text-gray-600">
											{new Date(record.record_date).toLocaleDateString()}
										</span>
										<div className="flex gap-4 text-sm">
											<span>A: {formatPercentage(record.availability)}</span>
											<span>P: {formatPercentage(record.performance)}</span>
											<span>Q: {formatPercentage(record.quality)}</span>
											<span className="font-bold">OEE: {formatPercentage(record.oee)}</span>
										</div>
									</div>
								))}
							</div>
						)}
					</div>
				</>
			) : (
				<div className="flex items-center justify-center py-12">
					<p className="text-gray-500">No data available</p>
				</div>
			)}
		</div>
	);
}
