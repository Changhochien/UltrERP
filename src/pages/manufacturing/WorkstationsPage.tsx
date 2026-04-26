/** Workstations Page - Manufacturing workstations workspace. */

import { WorkstationList } from "@/domain/manufacturing/components/WorkstationList";

export function WorkstationsPage() {
	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold text-gray-900">Workstations</h1>
			<WorkstationList showCreateButton={false} />
		</div>
	);
}
