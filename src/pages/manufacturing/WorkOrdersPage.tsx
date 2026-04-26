/** Work Orders Page - Manufacturing work orders workspace. */

import { WorkOrderList } from "@/domain/manufacturing/components/WorkOrderList";

export function WorkOrdersPage() {
	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold text-gray-900">Work Orders</h1>
			<WorkOrderList showCreateButton={false} />
		</div>
	);
}
