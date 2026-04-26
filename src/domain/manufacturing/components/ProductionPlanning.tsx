/** Production Planning Component - Manufacturing proposals and planning. */

import { useState } from "react";
import { useProposalActions, useProposals } from "../hooks/useBoms";
import type { ManufacturingProposalStatus } from "../types";

const STATUS_LABELS: Record<ManufacturingProposalStatus, string> = {
	proposed: "Proposed",
	accepted: "Accepted",
	rejected: "Rejected",
	stale: "Stale",
};

const STATUS_COLORS: Record<ManufacturingProposalStatus, string> = {
	proposed: "bg-blue-100 text-blue-800",
	accepted: "bg-green-100 text-green-800",
	rejected: "bg-red-100 text-red-800",
	stale: "bg-gray-100 text-gray-800",
};

export function ProductionPlanning() {
	const { proposals, isLoading, isError, refresh } = useProposals({});
	const { generateProposals, decideProposal } = useProposalActions();
	const [isGenerating, setIsGenerating] = useState(false);
	const [selectedProposals, setSelectedProposals] = useState<Set<string>>(new Set());

	if (isError) {
		return (
			<div className="rounded-md bg-red-50 p-4">
				<p className="text-sm text-red-700">Failed to load proposals</p>
			</div>
		);
	}

	const handleGenerate = async () => {
		setIsGenerating(true);
		try {
			await generateProposals();
			refresh();
		} catch (err) {
			alert(err instanceof Error ? err.message : "Failed to generate proposals");
		} finally {
			setIsGenerating(false);
		}
	};

	const handleAccept = async (proposalId: string) => {
		try {
			await decideProposal(proposalId, { decision: "accept" });
			refresh();
		} catch (err) {
			alert(err instanceof Error ? err.message : "Failed to accept proposal");
		}
	};

	const handleReject = async (proposalId: string) => {
		try {
			await decideProposal(proposalId, { decision: "reject" });
			refresh();
		} catch (err) {
			alert(err instanceof Error ? err.message : "Failed to reject proposal");
		}
	};

	const toggleSelect = (id: string) => {
		const newSet = new Set(selectedProposals);
		if (newSet.has(id)) {
			newSet.delete(id);
		} else {
			newSet.add(id);
		}
		setSelectedProposals(newSet);
	};

	return (
		<div className="space-y-4">
			<div className="flex items-center justify-between">
				<h2 className="text-lg font-medium text-gray-900">Manufacturing Proposals</h2>
				<button
					onClick={handleGenerate}
					disabled={isGenerating}
					className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
				>
					{isGenerating ? "Generating..." : "Generate Proposals"}
				</button>
			</div>

			<div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
				<table className="min-w-full divide-y divide-gray-200">
					<thead className="bg-gray-50">
						<tr>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Select</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Product</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Status</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Demand</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Proposed</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Available</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Shortages</th>
							<th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Actions</th>
						</tr>
					</thead>
					<tbody className="divide-y divide-gray-200">
						{isLoading ? (
							<tr>
								<td colSpan={8} className="px-4 py-8 text-center text-gray-500">
									Loading...
								</td>
							</tr>
						) : proposals.length === 0 ? (
							<tr>
								<td colSpan={8} className="px-4 py-8 text-center text-gray-500">
									No proposals. Click "Generate Proposals" to create them.
								</td>
							</tr>
						) : (
							proposals.map((proposal) => (
								<tr key={proposal.id} className="hover:bg-gray-50">
									<td className="px-4 py-3">
										<input
											type="checkbox"
											checked={selectedProposals.has(proposal.id)}
											onChange={() => toggleSelect(proposal.id)}
											disabled={proposal.status !== "proposed"}
											className="h-4 w-4 rounded border-gray-300"
										/>
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-900">
										{proposal.product_id}
									</td>
									<td className="whitespace-nowrap px-4 py-3">
										<span
											className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${STATUS_COLORS[proposal.status]}`}
										>
											{STATUS_LABELS[proposal.status]}
										</span>
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										{proposal.demand_quantity}
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										{proposal.proposed_quantity}
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
										{proposal.available_quantity}
									</td>
									<td className="whitespace-nowrap px-4 py-3 text-sm">
										{proposal.shortages && proposal.shortages.length > 0 ? (
											<span className="text-red-600">
												{proposal.shortages.length} items
											</span>
										) : (
											<span className="text-green-600">None</span>
										)}
									</td>
									<td className="whitespace-nowrap px-4 py-3">
										{proposal.status === "proposed" && (
											<div className="flex gap-2">
												<button
													onClick={() => handleAccept(proposal.id)}
													className="text-sm text-green-600 hover:text-green-800"
												>
													Accept
												</button>
												<button
													onClick={() => handleReject(proposal.id)}
													className="text-sm text-red-600 hover:text-red-800"
												>
													Reject
												</button>
											</div>
										)}
									</td>
								</tr>
							))
						)}
					</tbody>
				</table>
			</div>
		</div>
	);
}
