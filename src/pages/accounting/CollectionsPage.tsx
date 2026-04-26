/**
 * Collections Page (Epic 26 - Story 26-5)
 * Placeholder - Implementation pending
 */

import { useTranslation } from "react-i18next";

export function CollectionsPage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          {t("routes.collections.label", "Collections")}
        </h1>
        <p className="text-muted-foreground">
          {t("routes.collections.description", "Track overdue invoices and dunning notices")}
        </p>
      </div>
      <div className="rounded-lg border border-border bg-card p-8 text-center">
        <p className="text-muted-foreground">
          {t("common.comingSoon", "Coming soon")} - Collections implementation pending
        </p>
      </div>
    </div>
  );
}
