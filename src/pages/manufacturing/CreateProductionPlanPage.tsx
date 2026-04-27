import { useNavigate } from "react-router-dom";

import { ProductionPlanForm } from "@/domain/manufacturing/components/ProductionPlanForm";
import { PRODUCTION_PLANS_ROUTE } from "@/lib/routes";

export function CreateProductionPlanPage() {
	const navigate = useNavigate();

	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold text-gray-900">Create Production Plan</h1>
			<ProductionPlanForm onSuccess={() => navigate(PRODUCTION_PLANS_ROUTE)} onCancel={() => navigate(PRODUCTION_PLANS_ROUTE)} />
		</div>
	);
}