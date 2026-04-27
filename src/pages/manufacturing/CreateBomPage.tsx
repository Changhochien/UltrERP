import { useNavigate } from "react-router-dom";

import { BomForm } from "@/domain/manufacturing/components/BomForm";
import { BOM_LIST_ROUTE } from "@/lib/routes";

export function CreateBomPage() {
	const navigate = useNavigate();

	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold text-gray-900">Create BOM</h1>
			<BomForm onSuccess={() => navigate(BOM_LIST_ROUTE)} onCancel={() => navigate(BOM_LIST_ROUTE)} />
		</div>
	);
}