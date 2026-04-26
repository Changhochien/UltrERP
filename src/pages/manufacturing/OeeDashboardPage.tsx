/** OEE Dashboard Page - Equipment effectiveness dashboard. */

import { OeeDashboard } from "@/domain/manufacturing/components/OeeDashboard";

export function OeeDashboardPage() {
	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold text-gray-900">OEE Dashboard</h1>
			<OeeDashboard />
		</div>
	);
}
