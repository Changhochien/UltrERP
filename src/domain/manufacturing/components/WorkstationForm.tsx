import { useState } from "react";

import { useWorkstationActions } from "../hooks/useBoms";

interface WorkstationFormProps {
	onSuccess?: () => void;
	onCancel?: () => void;
}

export function WorkstationForm({ onSuccess, onCancel }: WorkstationFormProps) {
	const { createWorkstation } = useWorkstationActions();
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [formData, setFormData] = useState({
		code: "",
		name: "",
		description: "",
		hourly_cost: "0",
		capacity: "1",
		hours: [{ day_of_week: "1", start_time: "09:00", end_time: "17:00" }],
	});

	const handleSubmit = async (event: React.FormEvent) => {
		event.preventDefault();
		setIsSubmitting(true);
		setError(null);

		try {
			await createWorkstation({
				code: formData.code,
				name: formData.name,
				description: formData.description || undefined,
				hourly_cost: formData.hourly_cost || undefined,
				capacity: Number.parseInt(formData.capacity, 10),
				hours: formData.hours.filter((hour) => hour.start_time && hour.end_time).map((hour) => ({ day_of_week: Number.parseInt(hour.day_of_week, 10), start_time: hour.start_time, end_time: hour.end_time })),
			});
			onSuccess?.();
		} catch (submitError) {
			setError(submitError instanceof Error ? submitError.message : "Failed to create workstation");
		} finally {
			setIsSubmitting(false);
		}
	};

	return (
		<form onSubmit={handleSubmit} className="space-y-6">
			{error ? <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
			<div className="grid grid-cols-1 gap-6 md:grid-cols-2">
				<div>
					<label className="block text-sm font-medium text-gray-700">Code</label>
					<input required type="text" value={formData.code} onChange={(event) => setFormData({ ...formData, code: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
				</div>
				<div>
					<label className="block text-sm font-medium text-gray-700">Name</label>
					<input required type="text" value={formData.name} onChange={(event) => setFormData({ ...formData, name: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
				</div>
				<div>
					<label className="block text-sm font-medium text-gray-700">Hourly Cost</label>
					<input type="number" min="0" step="0.01" value={formData.hourly_cost} onChange={(event) => setFormData({ ...formData, hourly_cost: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
				</div>
				<div>
					<label className="block text-sm font-medium text-gray-700">Capacity</label>
					<input type="number" min="1" step="1" value={formData.capacity} onChange={(event) => setFormData({ ...formData, capacity: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
				</div>
			</div>
			<div>
				<label className="block text-sm font-medium text-gray-700">Description</label>
				<textarea rows={3} value={formData.description} onChange={(event) => setFormData({ ...formData, description: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
			</div>
			<div className="rounded-lg border border-gray-200 bg-white p-6">
				<div className="mb-4 flex items-center justify-between">
					<h2 className="text-lg font-medium text-gray-900">Working Hours</h2>
					<button type="button" onClick={() => setFormData({ ...formData, hours: [...formData.hours, { day_of_week: "1", start_time: "09:00", end_time: "17:00" }] })} className="rounded-md border border-gray-300 px-3 py-2 text-sm">
						Add Time Slot
					</button>
				</div>
				<div className="space-y-4">
					{formData.hours.map((hour, index) => (
						<div key={`${hour.day_of_week}-${index}`} className="grid grid-cols-1 gap-4 md:grid-cols-4 md:items-end">
							<div>
								<label className="block text-sm font-medium text-gray-700">Day</label>
								<select value={hour.day_of_week} onChange={(event) => {
									const hours = [...formData.hours];
									hours[index] = { ...hour, day_of_week: event.target.value };
									setFormData({ ...formData, hours });
								}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2">
									<option value="1">Monday</option>
									<option value="2">Tuesday</option>
									<option value="3">Wednesday</option>
									<option value="4">Thursday</option>
									<option value="5">Friday</option>
									<option value="6">Saturday</option>
									<option value="0">Sunday</option>
								</select>
							</div>
							<div>
								<label className="block text-sm font-medium text-gray-700">Start</label>
								<input type="time" value={hour.start_time} onChange={(event) => {
									const hours = [...formData.hours];
									hours[index] = { ...hour, start_time: event.target.value };
									setFormData({ ...formData, hours });
								}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
							</div>
							<div>
								<label className="block text-sm font-medium text-gray-700">End</label>
								<input type="time" value={hour.end_time} onChange={(event) => {
									const hours = [...formData.hours];
									hours[index] = { ...hour, end_time: event.target.value };
									setFormData({ ...formData, hours });
								}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
							</div>
							<div>
								<button type="button" onClick={() => setFormData({ ...formData, hours: formData.hours.filter((_, hourIndex) => hourIndex !== index) })} disabled={formData.hours.length === 1} className="rounded-md border border-gray-300 px-3 py-2 text-sm disabled:opacity-50">
									Remove Slot
								</button>
							</div>
						</div>
					))}
				</div>
			</div>
			<div className="flex items-center justify-end gap-4">
				{onCancel ? <button type="button" onClick={onCancel} className="rounded-md border border-gray-300 px-4 py-2 text-sm">Cancel</button> : null}
				<button type="submit" disabled={isSubmitting} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
					{isSubmitting ? "Creating..." : "Create Workstation"}
				</button>
			</div>
		</form>
	);
}