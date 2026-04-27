/** BOM List Page - Bill of Materials workspace. */

import { BomList } from "@/domain/manufacturing/components/BomList";

export function BomListPage() {
	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold text-gray-900">Bill of Materials</h1>
			<BomList />
		</div>
	);
}
