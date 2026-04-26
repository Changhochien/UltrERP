/**
 * Budgets Page (Epic 26 - Story 26-6)
 * Placeholder - Implementation pending
 */

import { useTranslation } from "react-i18next";

export function BudgetsPage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          {t("routes.budgets.label", "Budgets")}
        </h1>
        <p className="text-muted-foreground">
          {t("routes.budgets.description", "Create and manage budgets with period allocation")}
        </p>
      </div>
      <div className="rounded-lg border border-border bg-card p-8 text-center">
        <p className="text-muted-foreground">
          {t("common.comingSoon", "Coming soon")} - Budgets implementation pending
        </p>
      </div>
    </div>
  );
}
