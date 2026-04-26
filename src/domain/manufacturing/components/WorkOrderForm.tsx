/** Work Order Form Component - Create new work order. */

import { useState } from "react";
import { useWorkOrderActions } from "../hooks/useBoms";

interface WorkOrderFormProps {
	onSuccess?: () => void;
	onCancel?: () => void;
}

export function WorkOrderForm({ onSuccess, onCancel }: WorkOrderFormProps) {
	const { createWorkOrder } = useWorkOrderActions();
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const [formData, setFormData] = useState({
		product_id: "",
		bom_id: "",
		quantity: "1",
		source_warehouse_id: "",
		wip_warehouse_id: "",
		fg_warehouse_id: "",
		transfer_mode: "direct" as "direct" | "manufacture",
		planned_start_date: "",
		due_date: "",
		notes: "",
	});

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setIsSubmitting(true);
		setError(null);

		try {
			await createWorkOrder({
				product_id: formData.product_id,
				bom_id: formData.bom_id,
				quantity: formData.quantity,
				source_warehouse_id: formData.source_warehouse_id || undefined,
				wip_warehouse_id: formData.wip_warehouse_id || undefined,
				fg_warehouse_id: formData.fg_warehouse_id || undefined,
				transfer_mode: formData.transfer_mode,
				planned_start_date: formData.planned_start_date || undefined,
				due_date: formData.due_date || undefined,
				notes: formData.notes || undefined,
			});
			onSuccess?.();
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to create work order");
		} finally {
			setIsSubmitting(false);
		}
	};

	return (
		<form onSubmit={handleSubmit} className="space-y-6">
			{error && (
				<div className="rounded-md bg-red-50 p-4">
					<p className="text-sm text-red-700">{error}</p>
				</div>
			)}

			<div className="grid grid-cols-1 gap-6 md:grid-cols-2">
				<div>
					<label className="block text-sm font-medium text-gray-700">
						Product ID <span className="text-red-500">*</span>
					</label>
					<input
						type="text"
						required
						value={formData.product_id}
						onChange={(e) => setFormData({ ...formData, product_id: e.target.value })}
						className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
					/>
				</div>

				<div>
					<label className="block text-sm font-medium text-gray-700">
						BOM ID <span className="text-red-500">*</span>
					</label>
					<input
						type="text"
						required
						value={formData.bom_id}
						onChange={(e) => setFormData({ ...formData, bom_id: e.target.value })}
						className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
					/>
					<p className="mt-1 text-xs text-gray-500">
						Must be a submitted BOM
					</p>
				</div>

				<div>
					<label className="block text-sm font-medium text-gray-700">
						Quantity <span className="text-red-500">*</span>
					</label>
					<input
						type="number"
						required
						min="0.000001"
						step="0.000001"
						value={formData.quantity}
						onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
						className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
					/>
				</div>

				<div>
					<label className="block text-sm font-medium text-gray-700">Transfer Mode</label>
					<select
						value={formData.transfer_mode}
						onChange={(e) => setFormData({ ...formData, transfer_mode: e.target.value as "direct" | "manufacture" })}
						className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
					>
						<option value="direct">Direct Transfer</option>
						<option value="manufacture">Manufacture</option>
					</select>
				</div>

				<div>
					<label className="block text-sm font-medium text-gray-700">Source Warehouse</label>
					<input
						type="text"
						value={formData.source_warehouse_id}
						onChange={(e) => setFormData({ ...formData, source_warehouse_id: e.target.value })}
						placeholder="Warehouse ID"
						className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
					/>
				</div>

				<div>
					<label className="block text-sm font-medium text-gray-700">WIP Warehouse</label>
					<input
						type="text"
						value={formData.wip_warehouse_id}
						onChange={(e) => setFormData({ ...formData, wip_warehouse_id: e.target.value })}
						placeholder="Warehouse ID"
						className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
					/>
				</div>

				<div>
					<label className="block text-sm font-medium text-gray-700">Finished Goods Warehouse</label>
					<input
						type="text"
						value={formData.fg_warehouse_id}
						onChange={(e) => setFormData({ ...formData, fg_warehouse_id: e.target.value })}
						placeholder="Warehouse ID"
						className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
					/>
				</div>

				<div>
					<label className="block text-sm font-medium text-gray-700">Planned Start Date</label>
					<input
						type="datetime-local"
						value={formData.planned_start_date}
						onChange={(e) => setFormData({ ...formData, planned_start_date: e.target.value })}
						className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
					/>
				</div>

				<div>
					<label className="block text-sm font-medium text-gray-700">Due Date</label>
					<input
						type="datetime-local"
						value={formData.due_date}
						onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
						className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
					/>
				</div>
			</div>

			<div>
				<label className="block text-sm font-medium text-gray-700">Notes</label>
				<textarea
					value={formData.notes}
					onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
					rows={3}
					className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
				/>
			</div>

			<div className="flex items-center justify-end gap-4">
				{onCancel && (
					<button
						type="button"
						onClick={onCancel}
						className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
					>
						Cancel
					</button>
				)}
				<button
					type="submit"
					disabled={isSubmitting}
					className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
				>
					{isSubmitting ? "Creating..." : "Create Work Order"}
				</button>
			</div>
		</form>
	);
}
