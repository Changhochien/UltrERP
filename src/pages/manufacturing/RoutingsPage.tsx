/** Routings Page - Manufacturing routing templates workspace. */

import { RoutingList } from "@/domain/manufacturing/components/RoutingList";

export function RoutingsPage() {
	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold text-gray-900">Routing Templates</h1>
			<RoutingList showCreateButton={false} />
		</div>
	);
}
