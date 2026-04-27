import { useState } from "react";

import { useBomActions } from "../hooks/useBoms";

interface BomFormProps {
	onSuccess?: () => void;
	onCancel?: () => void;
}

export function BomForm({ onSuccess, onCancel }: BomFormProps) {
	const { createBom } = useBomActions();
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [formData, setFormData] = useState({
		product_id: "",
		code: "",
		name: "",
		bom_quantity: "1",
		unit: "pcs",
		revision: "",
		routing_id: "",
		notes: "",
		items: [
			{
				item_id: "",
				item_code: "",
				item_name: "",
				required_quantity: "1",
				unit: "pcs",
				source_warehouse_id: "",
				notes: "",
			},
		],
	});

	const handleSubmit = async (event: React.FormEvent) => {
		event.preventDefault();
		setIsSubmitting(true);
		setError(null);

		const items = formData.items.filter((item) => item.item_id && item.item_code && item.item_name);
		if (items.length === 0) {
			setError("At least one BOM item is required");
			setIsSubmitting(false);
			return;
		}

		try {
			await createBom({
				product_id: formData.product_id,
				code: formData.code || undefined,
				name: formData.name || undefined,
				bom_quantity: formData.bom_quantity || undefined,
				unit: formData.unit || undefined,
				revision: formData.revision || undefined,
				routing_id: formData.routing_id || undefined,
				notes: formData.notes || undefined,
				items: items.map((item, index) => ({
					item_id: item.item_id,
					item_code: item.item_code,
					item_name: item.item_name,
					required_quantity: item.required_quantity,
					unit: item.unit || undefined,
					source_warehouse_id: item.source_warehouse_id || undefined,
					idx: index,
					notes: item.notes || undefined,
				})),
			});
			onSuccess?.();
		} catch (submitError) {
			setError(submitError instanceof Error ? submitError.message : "Failed to create BOM");
		} finally {
			setIsSubmitting(false);
		}
	};

	return (
		<form onSubmit={handleSubmit} className="space-y-6">
			{error ? <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
			<div className="grid grid-cols-1 gap-6 md:grid-cols-2">
				<div>
					<label className="block text-sm font-medium text-gray-700">Product ID</label>
					<input aria-label="Product ID" required type="text" value={formData.product_id} onChange={(event) => setFormData({ ...formData, product_id: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
				</div>
				<div>
					<label className="block text-sm font-medium text-gray-700">Code</label>
					<input aria-label="Code" type="text" value={formData.code} onChange={(event) => setFormData({ ...formData, code: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
				</div>
				<div>
					<label className="block text-sm font-medium text-gray-700">Name</label>
					<input aria-label="Name" type="text" value={formData.name} onChange={(event) => setFormData({ ...formData, name: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
				</div>
				<div>
					<label className="block text-sm font-medium text-gray-700">Revision</label>
					<input aria-label="Revision" type="text" value={formData.revision} onChange={(event) => setFormData({ ...formData, revision: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
				</div>
				<div>
					<label className="block text-sm font-medium text-gray-700">BOM Quantity</label>
					<input aria-label="BOM Quantity" required type="number" min="0.000001" step="0.000001" value={formData.bom_quantity} onChange={(event) => setFormData({ ...formData, bom_quantity: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
				</div>
				<div>
					<label className="block text-sm font-medium text-gray-700">Unit</label>
					<input aria-label="Unit" type="text" value={formData.unit} onChange={(event) => setFormData({ ...formData, unit: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
				</div>
				<div className="md:col-span-2">
					<label className="block text-sm font-medium text-gray-700">Routing ID</label>
					<input aria-label="Routing ID" type="text" value={formData.routing_id} onChange={(event) => setFormData({ ...formData, routing_id: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
				</div>
			</div>

			<div className="rounded-lg border border-gray-200 bg-white p-6">
				<div className="mb-4 flex items-center justify-between">
					<h2 className="text-lg font-medium text-gray-900">Material Lines</h2>
					<button type="button" onClick={() => setFormData({ ...formData, items: [...formData.items, { item_id: "", item_code: "", item_name: "", required_quantity: "1", unit: "pcs", source_warehouse_id: "", notes: "" }] })} className="rounded-md border border-gray-300 px-3 py-2 text-sm">
						Add Item
					</button>
				</div>
				<div className="space-y-4">
					{formData.items.map((item, index) => (
						<div key={`${index}-${item.item_id}`} className="rounded-md border border-gray-200 p-4">
							<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
								<div>
									<label className="block text-sm font-medium text-gray-700">Item ID</label>
									<input aria-label="Item ID" required={index === 0} type="text" value={item.item_id} onChange={(event) => {
										const items = [...formData.items];
										items[index] = { ...item, item_id: event.target.value };
										setFormData({ ...formData, items });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700">Item Code</label>
									<input aria-label="Item Code" required={index === 0} type="text" value={item.item_code} onChange={(event) => {
										const items = [...formData.items];
										items[index] = { ...item, item_code: event.target.value };
										setFormData({ ...formData, items });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700">Item Name</label>
									<input aria-label="Item Name" required={index === 0} type="text" value={item.item_name} onChange={(event) => {
										const items = [...formData.items];
										items[index] = { ...item, item_name: event.target.value };
										setFormData({ ...formData, items });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700">Required Quantity</label>
									<input aria-label="Required Quantity" required={index === 0} type="number" min="0.000001" step="0.000001" value={item.required_quantity} onChange={(event) => {
										const items = [...formData.items];
										items[index] = { ...item, required_quantity: event.target.value };
										setFormData({ ...formData, items });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700">Unit</label>
									<input aria-label="Unit" type="text" value={item.unit} onChange={(event) => {
										const items = [...formData.items];
										items[index] = { ...item, unit: event.target.value };
										setFormData({ ...formData, items });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700">Source Warehouse ID</label>
									<input aria-label="Source Warehouse ID" type="text" value={item.source_warehouse_id} onChange={(event) => {
										const items = [...formData.items];
										items[index] = { ...item, source_warehouse_id: event.target.value };
										setFormData({ ...formData, items });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
							</div>
							<div className="mt-4 flex justify-end">
								<button type="button" onClick={() => setFormData({ ...formData, items: formData.items.filter((_, itemIndex) => itemIndex !== index) })} disabled={formData.items.length === 1} className="rounded-md border border-gray-300 px-3 py-2 text-sm disabled:opacity-50">
									Remove Item
								</button>
							</div>
						</div>
					))}
				</div>
			</div>

			<div>
				<label className="block text-sm font-medium text-gray-700">Notes</label>
				<textarea aria-label="Notes" rows={3} value={formData.notes} onChange={(event) => setFormData({ ...formData, notes: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
			</div>

			<div className="flex items-center justify-end gap-4">
				{onCancel ? <button type="button" onClick={onCancel} className="rounded-md border border-gray-300 px-4 py-2 text-sm">Cancel</button> : null}
				<button type="submit" disabled={isSubmitting} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
					{isSubmitting ? "Creating..." : "Create BOM"}
				</button>
			</div>
		</form>
	);
}