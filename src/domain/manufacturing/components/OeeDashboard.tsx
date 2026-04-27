/** OEE Dashboard Component - Equipment effectiveness dashboard. */

import { type FormEvent, useState } from "react";

import { useToast } from "@/hooks/useToast";

import {
	useDowntimeActions,
	useOeeActions,
	useOeeDashboard,
	useWorkOrders,
	useWorkstations,
} from "../hooks/useBoms";
import type { DowntimeReason } from "../types";

const DOWNTIME_REASON_OPTIONS: Array<{ value: DowntimeReason; label: string }> = [
	{ value: "unplanned_breakdown", label: "Unplanned breakdown" },
	{ value: "planned_maintenance", label: "Planned maintenance" },
	{ value: "changeover", label: "Changeover" },
	{ value: "material_shortage", label: "Material shortage" },
	{ value: "quality_hold", label: "Quality hold" },
];

function toLocalDateInput(date: Date): string {
	const offsetMs = date.getTimezoneOffset() * 60 * 1000;
	return new Date(date.getTime() - offsetMs).toISOString().slice(0, 10);
}

function toLocalDateTimeInput(date: Date): string {
	const offsetMs = date.getTimezoneOffset() * 60 * 1000;
	return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

function formatPercentage(value: number): string {
	return `${(value * 100).toFixed(1)}%`;
}

function formatReasonLabel(value: string): string {
	return value
		.split("_")
		.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
		.join(" ");
}

export function OeeDashboard() {
	const now = new Date();
	const [workstationId, setWorkstationId] = useState<string | undefined>(undefined);
	const [startDate, setStartDate] = useState<string>(
		toLocalDateInput(new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)),
	);
	const [endDate, setEndDate] = useState<string>(toLocalDateInput(now));
	const [isSubmittingDowntime, setIsSubmittingDowntime] = useState(false);
	const [isSubmittingOee, setIsSubmittingOee] = useState(false);
	const [downtimeForm, setDowntimeForm] = useState({
		workstation_id: "",
		work_order_id: "",
		reason: "unplanned_breakdown" as DowntimeReason,
		start_time: toLocalDateTimeInput(now),
		end_time: "",
		remarks: "",
	});
	const [oeeForm, setOeeForm] = useState({
		workstation_id: "",
		work_order_id: "",
		record_date: toLocalDateTimeInput(now),
		planned_production_time: "480",
		stop_time: "0",
		ideal_cycle_time: "1",
		total_count: "0",
		good_count: "0",
		reject_count: "0",
	});

	const { dashboard, isLoading, isError, refresh } = useOeeDashboard({
		workstation_id: workstationId,
		start_date: startDate,
		end_date: endDate,
	});
	const { workstations } = useWorkstations({ status: "active", page_size: 100 });
	const { workOrders } = useWorkOrders({ page_size: 100 });
	const { createDowntime } = useDowntimeActions();
	const { createOeeRecord } = useOeeActions();
	const { success: showSuccessToast, error: showErrorToast } = useToast();

	const selectableWorkOrders = workOrders.filter(
		(workOrder) => workOrder.status !== "completed" && workOrder.status !== "cancelled",
	);

	async function handleDowntimeSubmit(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		if (!downtimeForm.workstation_id) {
			showErrorToast("Workstation required", "Choose a workstation before logging downtime.");
			return;
		}

		setIsSubmittingDowntime(true);
		try {
			await createDowntime({
				workstation_id: downtimeForm.workstation_id,
				work_order_id: downtimeForm.work_order_id || null,
				reason: downtimeForm.reason,
				start_time: new Date(downtimeForm.start_time).toISOString(),
				end_time: downtimeForm.end_time ? new Date(downtimeForm.end_time).toISOString() : null,
				remarks: downtimeForm.remarks || null,
			});
			await refresh();
			showSuccessToast("Downtime logged", "The downtime event is now included in manufacturing reporting.");
			setDowntimeForm((current) => ({
				...current,
				work_order_id: "",
				start_time: toLocalDateTimeInput(new Date()),
				end_time: "",
				remarks: "",
			}));
		} catch (error) {
			showErrorToast(
				"Failed to log downtime",
				error instanceof Error ? error.message : "Unknown error",
			);
		} finally {
			setIsSubmittingDowntime(false);
		}
	}

	async function handleOeeSubmit(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		if (!oeeForm.workstation_id) {
			showErrorToast("Workstation required", "Choose a workstation before recording OEE.");
			return;
		}

		setIsSubmittingOee(true);
		try {
			await createOeeRecord({
				workstation_id: oeeForm.workstation_id,
				work_order_id: oeeForm.work_order_id || null,
				record_date: new Date(oeeForm.record_date).toISOString(),
				planned_production_time: Number.parseInt(oeeForm.planned_production_time, 10),
				stop_time: Number.parseInt(oeeForm.stop_time, 10),
				ideal_cycle_time: Number.parseInt(oeeForm.ideal_cycle_time, 10),
				total_count: Number.parseInt(oeeForm.total_count, 10),
				good_count: Number.parseInt(oeeForm.good_count, 10),
				reject_count: Number.parseInt(oeeForm.reject_count, 10),
			});
			await refresh();
			showSuccessToast("OEE recorded", "The production snapshot has been added to the OEE trend.");
			setOeeForm((current) => ({
				...current,
				work_order_id: "",
				record_date: toLocalDateTimeInput(new Date()),
				total_count: "0",
				good_count: "0",
				reject_count: "0",
				stop_time: "0",
			}));
		} catch (error) {
			showErrorToast(
				"Failed to record OEE",
				error instanceof Error ? error.message : "Unknown error",
			);
		} finally {
			setIsSubmittingOee(false);
		}
	}

	if (isError) {
		return (
			<div className="rounded-md bg-red-50 p-4">
				<p className="text-sm text-red-700">Failed to load OEE data</p>
			</div>
		);
	}

	return (
		<div className="space-y-6">
			<div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto_auto] xl:items-end">
				<div>
					<label htmlFor="oee-filter-workstation" className="block text-xs text-gray-500">
						Workstation
					</label>
					<select
						id="oee-filter-workstation"
						value={workstationId ?? ""}
						onChange={(event) => setWorkstationId(event.target.value || undefined)}
						className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
					>
						<option value="">All workstations</option>
						{workstations.map((workstation) => (
							<option key={workstation.id} value={workstation.id}>
								{workstation.code} - {workstation.name}
							</option>
						))}
					</select>
				</div>
				<div>
					<label htmlFor="oee-filter-from" className="block text-xs text-gray-500">
						From
					</label>
					<input
						id="oee-filter-from"
						type="date"
						value={startDate}
						onChange={(event) => setStartDate(event.target.value)}
						className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
					/>
				</div>
				<div>
					<label htmlFor="oee-filter-to" className="block text-xs text-gray-500">
						To
					</label>
					<input
						id="oee-filter-to"
						type="date"
						value={endDate}
						onChange={(event) => setEndDate(event.target.value)}
						className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
					/>
				</div>
				<div className="rounded-md border border-dashed border-gray-300 px-3 py-2 text-xs text-gray-500">
					{workstations.length === 0
						? "Create an active workstation before logging downtime or OEE."
						: `${workstations.length} active workstations available for logging.`}
				</div>
			</div>

			<div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
				<form onSubmit={handleDowntimeSubmit} className="rounded-lg border border-gray-200 bg-white p-6">
					<div className="mb-4 flex items-start justify-between gap-4">
						<div>
							<h2 className="text-lg font-medium text-gray-900">Log downtime</h2>
							<p className="mt-1 text-sm text-gray-500">
								Capture downtime events directly from the manufacturing dashboard.
							</p>
						</div>
					</div>
					<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
						<div>
							<label htmlFor="downtime-workstation" className="block text-xs text-gray-500">
								Downtime workstation
							</label>
							<select
								id="downtime-workstation"
								required
								value={downtimeForm.workstation_id}
								onChange={(event) =>
									setDowntimeForm((current) => ({
										...current,
										workstation_id: event.target.value,
									}))
								}
								className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
							>
								<option value="">Select workstation</option>
								{workstations.map((workstation) => (
									<option key={workstation.id} value={workstation.id}>
										{workstation.code} - {workstation.name}
									</option>
								))}
							</select>
						</div>
						<div>
							<label htmlFor="downtime-work-order" className="block text-xs text-gray-500">
								Downtime work order
							</label>
							<select
								id="downtime-work-order"
								value={downtimeForm.work_order_id}
								onChange={(event) =>
									setDowntimeForm((current) => ({
										...current,
										work_order_id: event.target.value,
									}))
								}
								className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
							>
								<option value="">No linked work order</option>
								{selectableWorkOrders.map((workOrder) => (
									<option key={workOrder.id} value={workOrder.id}>
										{workOrder.code} - {workOrder.name}
									</option>
								))}
							</select>
						</div>
						<div>
							<label htmlFor="downtime-reason" className="block text-xs text-gray-500">
								Downtime reason
							</label>
							<select
								id="downtime-reason"
								value={downtimeForm.reason}
								onChange={(event) =>
									setDowntimeForm((current) => ({
										...current,
										reason: event.target.value as DowntimeReason,
									}))
								}
								className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
							>
								{DOWNTIME_REASON_OPTIONS.map((option) => (
									<option key={option.value} value={option.value}>
										{option.label}
									</option>
								))}
							</select>
						</div>
						<div>
							<label htmlFor="downtime-start" className="block text-xs text-gray-500">
								Downtime start
							</label>
							<input
								id="downtime-start"
								required
								type="datetime-local"
								value={downtimeForm.start_time}
								onChange={(event) =>
									setDowntimeForm((current) => ({
										...current,
										start_time: event.target.value,
									}))
								}
								className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
							/>
						</div>
						<div>
							<label htmlFor="downtime-end" className="block text-xs text-gray-500">
								Downtime end
							</label>
							<input
								id="downtime-end"
								type="datetime-local"
								value={downtimeForm.end_time}
								onChange={(event) =>
									setDowntimeForm((current) => ({
										...current,
										end_time: event.target.value,
									}))
								}
								className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
							/>
						</div>
						<div className="md:col-span-2">
							<label htmlFor="downtime-notes" className="block text-xs text-gray-500">
								Downtime notes
							</label>
							<textarea
								id="downtime-notes"
								value={downtimeForm.remarks}
								onChange={(event) =>
									setDowntimeForm((current) => ({
										...current,
										remarks: event.target.value,
									}))
								}
								rows={3}
								className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
							/>
						</div>
					</div>
					<div className="mt-4 flex justify-end">
						<button
							type="submit"
							disabled={isSubmittingDowntime || workstations.length === 0}
							className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
						>
							{isSubmittingDowntime ? "Saving..." : "Log downtime"}
						</button>
					</div>
				</form>

				<form onSubmit={handleOeeSubmit} className="rounded-lg border border-gray-200 bg-white p-6">
					<div className="mb-4">
						<h2 className="text-lg font-medium text-gray-900">Record OEE</h2>
						<p className="mt-1 text-sm text-gray-500">
							Capture a production snapshot for OEE trend and factor reporting.
						</p>
					</div>
					<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
						<div>
							<label htmlFor="oee-workstation" className="block text-xs text-gray-500">
								OEE workstation
							</label>
							<select
								id="oee-workstation"
								required
								value={oeeForm.workstation_id}
								onChange={(event) =>
									setOeeForm((current) => ({
										...current,
										workstation_id: event.target.value,
									}))
								}
								className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
							>
								<option value="">Select workstation</option>
								{workstations.map((workstation) => (
									<option key={workstation.id} value={workstation.id}>
										{workstation.code} - {workstation.name}
									</option>
								))}
							</select>
						</div>
						<div>
							<label htmlFor="oee-work-order" className="block text-xs text-gray-500">
								OEE work order
							</label>
							<select
								id="oee-work-order"
								value={oeeForm.work_order_id}
								onChange={(event) =>
									setOeeForm((current) => ({
										...current,
										work_order_id: event.target.value,
									}))
								}
								className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
							>
								<option value="">No linked work order</option>
								{selectableWorkOrders.map((workOrder) => (
									<option key={workOrder.id} value={workOrder.id}>
										{workOrder.code} - {workOrder.name}
									</option>
								))}
							</select>
						</div>
						<div>
							<label htmlFor="oee-record-date" className="block text-xs text-gray-500">
								Record time
							</label>
							<input
								id="oee-record-date"
								required
								type="datetime-local"
								value={oeeForm.record_date}
								onChange={(event) =>
									setOeeForm((current) => ({
										...current,
										record_date: event.target.value,
									}))
								}
								className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
							/>
						</div>
						<div>
							<label htmlFor="oee-planned-minutes" className="block text-xs text-gray-500">
								Planned minutes
							</label>
							<input
								id="oee-planned-minutes"
								min={1}
								required
								type="number"
								value={oeeForm.planned_production_time}
								onChange={(event) =>
									setOeeForm((current) => ({
										...current,
										planned_production_time: event.target.value,
									}))
								}
								className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
							/>
						</div>
						<div>
							<label htmlFor="oee-stop-minutes" className="block text-xs text-gray-500">
								Stop minutes
							</label>
							<input
								id="oee-stop-minutes"
								min={0}
								type="number"
								value={oeeForm.stop_time}
								onChange={(event) =>
									setOeeForm((current) => ({
										...current,
										stop_time: event.target.value,
									}))
								}
								className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
							/>
						</div>
						<div>
							<label htmlFor="oee-ideal-cycle" className="block text-xs text-gray-500">
								Ideal cycle minutes
							</label>
							<input
								id="oee-ideal-cycle"
								min={1}
								required
								type="number"
								value={oeeForm.ideal_cycle_time}
								onChange={(event) =>
									setOeeForm((current) => ({
										...current,
										ideal_cycle_time: event.target.value,
									}))
								}
								className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
							/>
						</div>
						<div>
							<label htmlFor="oee-total-count" className="block text-xs text-gray-500">
								Total units
							</label>
							<input
								id="oee-total-count"
								min={0}
								type="number"
								value={oeeForm.total_count}
								onChange={(event) =>
									setOeeForm((current) => ({
										...current,
										total_count: event.target.value,
									}))
								}
								className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
							/>
						</div>
						<div>
							<label htmlFor="oee-good-count" className="block text-xs text-gray-500">
								Good units
							</label>
							<input
								id="oee-good-count"
								min={0}
								type="number"
								value={oeeForm.good_count}
								onChange={(event) =>
									setOeeForm((current) => ({
										...current,
										good_count: event.target.value,
									}))
								}
								className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
							/>
						</div>
						<div>
							<label htmlFor="oee-reject-count" className="block text-xs text-gray-500">
								Rejected units
							</label>
							<input
								id="oee-reject-count"
								min={0}
								type="number"
								value={oeeForm.reject_count}
								onChange={(event) =>
									setOeeForm((current) => ({
										...current,
										reject_count: event.target.value,
									}))
								}
								className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
							/>
						</div>
					</div>
					<div className="mt-4 flex justify-end">
						<button
							type="submit"
							disabled={isSubmittingOee || workstations.length === 0}
							className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
						>
							{isSubmittingOee ? "Saving..." : "Record OEE"}
						</button>
					</div>
				</form>
			</div>

			{isLoading ? (
				<div className="flex items-center justify-center py-12">
					<p className="text-gray-500">Loading...</p>
				</div>
			) : dashboard ? (
				<>
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

					<div className="rounded-lg border border-gray-200 bg-white p-6">
						<h2 className="mb-4 text-lg font-medium text-gray-900">Downtime Pareto</h2>
						{dashboard.downtime_pareto.length === 0 ? (
							<p className="py-8 text-center text-gray-500">No downtime data available</p>
						) : (
							<div className="space-y-2">
								{dashboard.downtime_pareto.map((item, index) => (
									<div key={item.reason} className="flex items-center gap-4">
										<div className="w-8 text-center font-medium text-gray-500">{index + 1}</div>
										<div className="flex-1">
											<div className="flex items-center justify-between text-sm">
												<span className="font-medium text-gray-700">
													{formatReasonLabel(item.reason)}
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

					<div className="rounded-lg border border-gray-200 bg-white p-6">
						<h2 className="mb-4 text-lg font-medium text-gray-900">OEE Trend</h2>
						{dashboard.trend_data.length === 0 ? (
							<p className="py-8 text-center text-gray-500">No OEE records available</p>
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
