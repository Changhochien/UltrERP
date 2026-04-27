import { useNavigate } from "react-router-dom";

import { RoutingForm } from "@/domain/manufacturing/components/RoutingForm";
import { ROUTINGS_ROUTE } from "@/lib/routes";

export function CreateRoutingPage() {
	const navigate = useNavigate();

	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold text-gray-900">Create Routing</h1>
			<RoutingForm onSuccess={() => navigate(ROUTINGS_ROUTE)} onCancel={() => navigate(ROUTINGS_ROUTE)} />
		</div>
	);
}