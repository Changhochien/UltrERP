import { useState } from "react";
import { useParams } from "react-router-dom";

import { useBom, useBomActions, useBomHistory } from "@/domain/manufacturing/hooks/useBoms";

export function BomDetailPage() {
	const { bomId } = useParams<{ bomId: string }>();
	const { bom, isLoading, isError, refresh } = useBom(bomId ?? null);
	const { history, refresh: refreshHistory } = useBomHistory(bom?.product_id ?? null);
	const { submitBom } = useBomActions();
	const [isSubmitting, setIsSubmitting] = useState(false);

	if (!bomId) {
		return <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">Missing BOM identifier.</div>;
	}

	if (isLoading) {
		return <div className="rounded-md border border-gray-200 bg-white p-6 text-sm text-gray-500">Loading BOM...</div>;
	}

	if (isError || !bom) {
		return <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">Failed to load BOM.</div>;
	}

	const handleSubmit = async () => {
		setIsSubmitting(true);
		try {
			await submitBom(bom.id);
			await Promise.all([refresh(), refreshHistory()]);
		} catch (error) {
			window.alert(error instanceof Error ? error.message : "Failed to submit BOM");
		} finally {
			setIsSubmitting(false);
		}
	};

	return (
		<div className="space-y-6">
			<div className="flex flex-col gap-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm lg:flex-row lg:items-start lg:justify-between">
				<div className="space-y-2">
					<p className="text-sm font-medium uppercase tracking-wide text-gray-500">Bill of Materials</p>
					<h1 className="text-2xl font-semibold text-gray-900">{bom.name}</h1>
					<p className="text-sm text-gray-500">Code {bom.code} · Product {bom.product_id}</p>
				</div>
				<div className="flex items-center gap-3">
					<span className="inline-flex rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-700">
						{bom.status}
					</span>
					{bom.status === "draft" && (
						<button
							onClick={handleSubmit}
							disabled={isSubmitting}
							className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
						>
							{isSubmitting ? "Submitting..." : "Submit BOM"}
						</button>
					)}
				</div>
			</div>

			<div className="grid gap-4 md:grid-cols-4">
				<div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
					<p className="text-xs uppercase tracking-wide text-gray-500">Revision</p>
					<p className="mt-2 text-lg font-semibold text-gray-900">{bom.revision || "-"}</p>
				</div>
				<div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
					<p className="text-xs uppercase tracking-wide text-gray-500">BOM Quantity</p>
					<p className="mt-2 text-lg font-semibold text-gray-900">{bom.bom_quantity} {bom.unit}</p>
				</div>
				<div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
					<p className="text-xs uppercase tracking-wide text-gray-500">Items</p>
					<p className="mt-2 text-lg font-semibold text-gray-900">{bom.item_count}</p>
				</div>
				<div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
					<p className="text-xs uppercase tracking-wide text-gray-500">Active Version</p>
					<p className="mt-2 text-lg font-semibold text-gray-900">{bom.is_active ? "Yes" : "No"}</p>
				</div>
			</div>

			<div className="rounded-xl border border-gray-200 bg-white shadow-sm">
				<div className="border-b border-gray-200 px-6 py-4">
					<h2 className="text-lg font-semibold text-gray-900">Materials</h2>
				</div>
				<div className="overflow-x-auto">
					<table className="min-w-full divide-y divide-gray-200">
						<thead className="bg-gray-50">
							<tr>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Item</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Quantity</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Unit</th>
								<th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">Source Warehouse</th>
							</tr>
						</thead>
						<tbody className="divide-y divide-gray-200">
							{bom.items.map((item) => (
								<tr key={item.id}>
									<td className="px-6 py-4 text-sm text-gray-900">{item.item_name}<div className="text-xs text-gray-500">{item.item_code}</div></td>
									<td className="px-6 py-4 text-sm text-gray-700">{item.required_quantity}</td>
									<td className="px-6 py-4 text-sm text-gray-700">{item.unit}</td>
									<td className="px-6 py-4 text-sm text-gray-700">{item.source_warehouse_id || "-"}</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			</div>

			<div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
				<h2 className="text-lg font-semibold text-gray-900">Revision History</h2>
				<div className="mt-4 space-y-3">
					{history.map((entry) => (
						<div key={entry.id} className="flex items-center justify-between rounded-lg border border-gray-200 px-4 py-3">
							<div>
								<p className="text-sm font-medium text-gray-900">{entry.code} · Revision {entry.revision || "-"}</p>
								<p className="text-xs text-gray-500">Created {new Date(entry.created_at).toLocaleString()}</p>
							</div>
							<div className="flex items-center gap-2">
								{entry.is_active && <span className="rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-700">Active</span>}
								<span className="rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-700">{entry.status}</span>
							</div>
						</div>
					))}
				</div>
			</div>
		</div>
	);
}