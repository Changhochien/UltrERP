import { useState } from "react";

import { useProductionPlanActions } from "../hooks/useBoms";

function toLocalDateInput(date: Date): string {
	const offsetMs = date.getTimezoneOffset() * 60 * 1000;
	return new Date(date.getTime() - offsetMs).toISOString().slice(0, 10);
}

interface ProductionPlanFormProps {
	onSuccess?: () => void;
	onCancel?: () => void;
}

export function ProductionPlanForm({ onSuccess, onCancel }: ProductionPlanFormProps) {
	const { createProductionPlan } = useProductionPlanActions();
	const now = new Date();
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [formData, setFormData] = useState({
		name: "",
		planning_strategy: "make_to_order",
		start_date: toLocalDateInput(now),
		end_date: toLocalDateInput(new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)),
		notes: "",
		lines: [{ product_id: "", bom_id: "", routing_id: "", forecast_demand: "0", proposed_qty: "0", notes: "" }],
	});

	const handleSubmit = async (event: React.FormEvent) => {
		event.preventDefault();
		setIsSubmitting(true);
		setError(null);

		const lines = formData.lines.filter((line) => line.product_id.trim());
		if (lines.length === 0) {
			setError("At least one production-plan line is required");
			setIsSubmitting(false);
			return;
		}

		try {
			await createProductionPlan({
				name: formData.name,
				planning_strategy: formData.planning_strategy,
				start_date: formData.start_date,
				end_date: formData.end_date,
				notes: formData.notes || undefined,
				lines: lines.map((line, index) => ({
					product_id: line.product_id,
					bom_id: line.bom_id || undefined,
					routing_id: line.routing_id || undefined,
					forecast_demand: line.forecast_demand || undefined,
					proposed_qty: line.proposed_qty || undefined,
					idx: index,
					notes: line.notes || undefined,
				})),
			});
			onSuccess?.();
		} catch (submitError) {
			setError(submitError instanceof Error ? submitError.message : "Failed to create production plan");
		} finally {
			setIsSubmitting(false);
		}
	};

	return (
		<form onSubmit={handleSubmit} className="space-y-6">
			{error ? <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
			<div className="grid grid-cols-1 gap-6 md:grid-cols-2">
				<div>
					<label className="block text-sm font-medium text-gray-700">Name</label>
					<input aria-label="Name" required type="text" value={formData.name} onChange={(event) => setFormData({ ...formData, name: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
				</div>
				<div>
					<label className="block text-sm font-medium text-gray-700">Planning Strategy</label>
					<select aria-label="Planning Strategy" value={formData.planning_strategy} onChange={(event) => setFormData({ ...formData, planning_strategy: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2">
						<option value="make_to_order">Make to Order</option>
						<option value="make_to_stock">Make to Stock</option>
					</select>
				</div>
				<div>
					<label className="block text-sm font-medium text-gray-700">Start Date</label>
					<input aria-label="Start Date" required type="date" value={formData.start_date} onChange={(event) => setFormData({ ...formData, start_date: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
				</div>
				<div>
					<label className="block text-sm font-medium text-gray-700">End Date</label>
					<input aria-label="End Date" required type="date" value={formData.end_date} onChange={(event) => setFormData({ ...formData, end_date: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
				</div>
			</div>
			<div>
				<label className="block text-sm font-medium text-gray-700">Notes</label>
				<textarea aria-label="Notes" rows={3} value={formData.notes} onChange={(event) => setFormData({ ...formData, notes: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
			</div>
			<div className="rounded-lg border border-gray-200 bg-white p-6">
				<div className="mb-4 flex items-center justify-between">
					<h2 className="text-lg font-medium text-gray-900">Plan Lines</h2>
					<button type="button" onClick={() => setFormData({ ...formData, lines: [...formData.lines, { product_id: "", bom_id: "", routing_id: "", forecast_demand: "0", proposed_qty: "0", notes: "" }] })} className="rounded-md border border-gray-300 px-3 py-2 text-sm">
						Add Line
					</button>
				</div>
				<div className="space-y-4">
					{formData.lines.map((line, index) => (
						<div key={`${line.product_id}-${index}`} className="rounded-md border border-gray-200 p-4">
							<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
								<div>
									<label className="block text-sm font-medium text-gray-700">Product ID</label>
									<input aria-label="Product ID" required={index === 0} type="text" value={line.product_id} onChange={(event) => {
										const lines = [...formData.lines];
										lines[index] = { ...line, product_id: event.target.value };
										setFormData({ ...formData, lines });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700">BOM ID</label>
									<input aria-label="BOM ID" type="text" value={line.bom_id} onChange={(event) => {
										const lines = [...formData.lines];
										lines[index] = { ...line, bom_id: event.target.value };
										setFormData({ ...formData, lines });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700">Routing ID</label>
									<input aria-label="Routing ID" type="text" value={line.routing_id} onChange={(event) => {
										const lines = [...formData.lines];
										lines[index] = { ...line, routing_id: event.target.value };
										setFormData({ ...formData, lines });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700">Forecast Demand</label>
									<input aria-label="Forecast Demand" type="number" min="0" step="0.000001" value={line.forecast_demand} onChange={(event) => {
										const lines = [...formData.lines];
										lines[index] = { ...line, forecast_demand: event.target.value };
										setFormData({ ...formData, lines });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700">Proposed Quantity</label>
									<input aria-label="Proposed Quantity" type="number" min="0" step="0.000001" value={line.proposed_qty} onChange={(event) => {
										const lines = [...formData.lines];
										lines[index] = { ...line, proposed_qty: event.target.value };
										setFormData({ ...formData, lines });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
							</div>
							<div className="mt-4 flex justify-end">
								<button type="button" onClick={() => setFormData({ ...formData, lines: formData.lines.filter((_, lineIndex) => lineIndex !== index) })} disabled={formData.lines.length === 1} className="rounded-md border border-gray-300 px-3 py-2 text-sm disabled:opacity-50">
									Remove Line
								</button>
							</div>
						</div>
					))}
				</div>
			</div>
			<div className="flex items-center justify-end gap-4">
				{onCancel ? <button type="button" onClick={onCancel} className="rounded-md border border-gray-300 px-4 py-2 text-sm">Cancel</button> : null}
				<button type="submit" disabled={isSubmitting} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
					{isSubmitting ? "Creating..." : "Create Production Plan"}
				</button>
			</div>
		</form>
	);
}