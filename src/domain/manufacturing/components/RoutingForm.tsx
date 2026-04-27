import { useState } from "react";

import { useRoutingActions, useWorkstations } from "../hooks/useBoms";

interface RoutingFormProps {
	onSuccess?: () => void;
	onCancel?: () => void;
}

export function RoutingForm({ onSuccess, onCancel }: RoutingFormProps) {
	const { createRouting } = useRoutingActions();
	const { workstations } = useWorkstations({ status: "active", page_size: 100 });
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [formData, setFormData] = useState({
		code: "",
		name: "",
		description: "",
		operations: [{ operation_name: "", workstation_id: "", sequence: "1", setup_minutes: "0", fixed_run_minutes: "0", variable_run_minutes_per_unit: "1", batch_size: "1", overlap_lag_minutes: "0", notes: "" }],
	});

	const handleSubmit = async (event: React.FormEvent) => {
		event.preventDefault();
		setIsSubmitting(true);
		setError(null);

		const operations = formData.operations.filter((operation) => operation.operation_name.trim());
		if (operations.length === 0) {
			setError("At least one routing operation is required");
			setIsSubmitting(false);
			return;
		}

		try {
			await createRouting({
				code: formData.code,
				name: formData.name,
				description: formData.description || undefined,
				operations: operations.map((operation, index) => ({
					operation_name: operation.operation_name,
					workstation_id: operation.workstation_id || undefined,
					sequence: Number.parseInt(operation.sequence, 10),
					setup_minutes: Number.parseInt(operation.setup_minutes, 10),
					fixed_run_minutes: Number.parseInt(operation.fixed_run_minutes, 10),
					variable_run_minutes_per_unit: operation.variable_run_minutes_per_unit,
					batch_size: Number.parseInt(operation.batch_size, 10),
					overlap_lag_minutes: Number.parseInt(operation.overlap_lag_minutes, 10),
					idx: index,
					notes: operation.notes || undefined,
				})),
			});
			onSuccess?.();
		} catch (submitError) {
			setError(submitError instanceof Error ? submitError.message : "Failed to create routing");
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
					<input aria-label="Code" required type="text" value={formData.code} onChange={(event) => setFormData({ ...formData, code: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
				</div>
				<div>
					<label className="block text-sm font-medium text-gray-700">Name</label>
					<input aria-label="Name" required type="text" value={formData.name} onChange={(event) => setFormData({ ...formData, name: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
				</div>
			</div>
			<div>
				<label className="block text-sm font-medium text-gray-700">Description</label>
				<textarea aria-label="Description" rows={3} value={formData.description} onChange={(event) => setFormData({ ...formData, description: event.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
			</div>
			<div className="rounded-lg border border-gray-200 bg-white p-6">
				<div className="mb-4 flex items-center justify-between">
					<h2 className="text-lg font-medium text-gray-900">Operations</h2>
					<button type="button" onClick={() => setFormData({ ...formData, operations: [...formData.operations, { operation_name: "", workstation_id: "", sequence: String(formData.operations.length + 1), setup_minutes: "0", fixed_run_minutes: "0", variable_run_minutes_per_unit: "1", batch_size: "1", overlap_lag_minutes: "0", notes: "" }] })} className="rounded-md border border-gray-300 px-3 py-2 text-sm">
						Add Operation
					</button>
				</div>
				<div className="space-y-4">
					{formData.operations.map((operation, index) => (
						<div key={`${operation.sequence}-${index}`} className="rounded-md border border-gray-200 p-4">
							<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
								<div>
									<label className="block text-sm font-medium text-gray-700">Operation Name</label>
									<input aria-label="Operation Name" required={index === 0} type="text" value={operation.operation_name} onChange={(event) => {
										const operations = [...formData.operations];
										operations[index] = { ...operation, operation_name: event.target.value };
										setFormData({ ...formData, operations });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700">Workstation</label>
									<select aria-label="Workstation" value={operation.workstation_id} onChange={(event) => {
										const operations = [...formData.operations];
										operations[index] = { ...operation, workstation_id: event.target.value };
										setFormData({ ...formData, operations });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2">
										<option value="">No workstation</option>
										{workstations.map((workstation) => <option key={workstation.id} value={workstation.id}>{workstation.code} - {workstation.name}</option>)}
									</select>
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700">Sequence</label>
									<input aria-label="Sequence" type="number" min="1" step="1" value={operation.sequence} onChange={(event) => {
										const operations = [...formData.operations];
										operations[index] = { ...operation, sequence: event.target.value };
										setFormData({ ...formData, operations });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700">Setup Minutes</label>
									<input aria-label="Setup Minutes" type="number" min="0" step="1" value={operation.setup_minutes} onChange={(event) => {
										const operations = [...formData.operations];
										operations[index] = { ...operation, setup_minutes: event.target.value };
										setFormData({ ...formData, operations });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700">Fixed Run Minutes</label>
									<input aria-label="Fixed Run Minutes" type="number" min="0" step="1" value={operation.fixed_run_minutes} onChange={(event) => {
										const operations = [...formData.operations];
										operations[index] = { ...operation, fixed_run_minutes: event.target.value };
										setFormData({ ...formData, operations });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700">Variable Run Minutes / Unit</label>
									<input aria-label="Variable Run Minutes / Unit" type="number" min="0" step="0.000001" value={operation.variable_run_minutes_per_unit} onChange={(event) => {
										const operations = [...formData.operations];
										operations[index] = { ...operation, variable_run_minutes_per_unit: event.target.value };
										setFormData({ ...formData, operations });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700">Batch Size</label>
									<input aria-label="Batch Size" type="number" min="1" step="1" value={operation.batch_size} onChange={(event) => {
										const operations = [...formData.operations];
										operations[index] = { ...operation, batch_size: event.target.value };
										setFormData({ ...formData, operations });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700">Overlap Lag Minutes</label>
									<input aria-label="Overlap Lag Minutes" type="number" min="0" step="1" value={operation.overlap_lag_minutes} onChange={(event) => {
										const operations = [...formData.operations];
										operations[index] = { ...operation, overlap_lag_minutes: event.target.value };
										setFormData({ ...formData, operations });
									}} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2" />
								</div>
							</div>
							<div className="mt-4 flex justify-end">
								<button type="button" onClick={() => setFormData({ ...formData, operations: formData.operations.filter((_, operationIndex) => operationIndex !== index) })} disabled={formData.operations.length === 1} className="rounded-md border border-gray-300 px-3 py-2 text-sm disabled:opacity-50">
									Remove Operation
								</button>
							</div>
						</div>
					))}
				</div>
			</div>
			<div className="flex items-center justify-end gap-4">
				{onCancel ? <button type="button" onClick={onCancel} className="rounded-md border border-gray-300 px-4 py-2 text-sm">Cancel</button> : null}
				<button type="submit" disabled={isSubmitting} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
					{isSubmitting ? "Creating..." : "Create Routing"}
				</button>
			</div>
		</form>
	);
}