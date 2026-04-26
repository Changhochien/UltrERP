/**
 * Bank Reconciliation Page (Epic 26 - Story 26-5)
 * Placeholder - Implementation pending
 */

import { useTranslation } from "react-i18next";

export function BankReconciliationPage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          {t("routes.bankReconciliation.label", "Bank Reconciliation")}
        </h1>
        <p className="text-muted-foreground">
          {t("routes.bankReconciliation.description", "Import bank statements and reconcile with ledger")}
        </p>
      </div>
      <div className="rounded-lg border border-border bg-card p-8 text-center">
        <p className="text-muted-foreground">
          {t("common.comingSoon", "Coming soon")} - Bank Reconciliation implementation pending
        </p>
      </div>
    </div>
  );
}
