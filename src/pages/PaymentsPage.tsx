import ReconciliationScreen from "../domain/payments/components/ReconciliationScreen";
import { useTranslation } from "react-i18next";
import { PageHeader, SectionCard } from "../components/layout/PageLayout";

export function PaymentsPage() {
  const { t } = useTranslation("payments");
  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: t("page.title") }]}
        eyebrow={t("page.title")}
        title={t("page.title")}
        description={t("page.description")}
      />

      <SectionCard title={t("reconciliation.title")} description={t("reconciliation.description")}>
        <ReconciliationScreen />
      </SectionCard>
    </div>
  );
}
