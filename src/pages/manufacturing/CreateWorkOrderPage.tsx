/** Create Work Order Page - Create new manufacturing work order. */

import { WorkOrderForm } from "@/domain/manufacturing/components/WorkOrderForm";
import { useRouter } from "next/router";

export function CreateWorkOrderPage() {
	const router = useRouter();

	const handleSuccess = () => {
		router.push("/manufacturing/work-orders");
	};

	const handleCancel = () => {
		router.push("/manufacturing/work-orders");
	};

	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold text-gray-900">Create Work Order</h1>
			<WorkOrderForm onSuccess={handleSuccess} onCancel={handleCancel} />
		</div>
	);
}
