/** Production Planning Page - Manufacturing proposals and planning workspace. */

import { ProductionPlanning } from "@/domain/manufacturing/components/ProductionPlanning";

export function ProductionPlanningPage() {
	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold text-gray-900">Production Planning</h1>
			<ProductionPlanning />
		</div>
	);
}
