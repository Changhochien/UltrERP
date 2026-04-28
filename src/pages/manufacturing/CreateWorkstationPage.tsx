import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { WorkstationForm } from "@/domain/manufacturing/components/WorkstationForm";
import { WORKSTATIONS_ROUTE } from "@/lib/routes";

export function CreateWorkstationPage() {
  const { t } = useTranslation("manufacturing");

	const navigate = useNavigate();

	return (
		<div className="space-y-6">
			<h1 className="text-2xl font-bold text-gray-900">{t("createWorkstation.title")}</h1>
			<WorkstationForm onSuccess={() => navigate(WORKSTATIONS_ROUTE)} onCancel={() => navigate(WORKSTATIONS_ROUTE)} />
		</div>
	);
}