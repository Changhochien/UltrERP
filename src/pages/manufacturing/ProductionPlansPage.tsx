/** Production Plans Page - Production plan management workspace. */

import { ProductionPlanList } from "@/domain/manufacturing/components/ProductionPlanList";

export function ProductionPlansPage() {
	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold text-gray-900">Production Plans</h1>
			<ProductionPlanList />
		</div>
	);
}
