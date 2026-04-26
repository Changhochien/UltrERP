/** Create Work Order Page - Create new manufacturing work order. */

import { useNavigate } from "react-router-dom";
import { WorkOrderForm } from "@/domain/manufacturing/components/WorkOrderForm";

export function CreateWorkOrderPage() {
	const navigate = useNavigate();

	const handleSuccess = () => {
		navigate("/manufacturing/work-orders");
	};

	const handleCancel = () => {
		navigate("/manufacturing/work-orders");
	};

	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold text-gray-900">Create Work Order</h1>
			<WorkOrderForm onSuccess={handleSuccess} onCancel={handleCancel} />
		</div>
	);
}
