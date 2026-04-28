import { useTranslation } from "react-i18next";

import { AffinityMatrix } from "../domain/intelligence/components/AffinityMatrix";
import { CategoryTrendRadar } from "../domain/intelligence/components/CategoryTrendRadar";
import { CustomerBuyingBehaviorCard } from "../domain/intelligence/components/CustomerBuyingBehaviorCard";
import { ProspectGapTable } from "../domain/intelligence/components/ProspectGapTable";
import { ProductPerformanceCard } from "../domain/intelligence/components/ProductPerformanceCard";
import { RevenueDiagnosisCard } from "../domain/intelligence/components/RevenueDiagnosisCard";
import { RiskSignalFeed } from "../domain/intelligence/components/RiskSignalFeed";
import { PageHeader, SectionCard, SurfaceMessage } from "../components/layout/PageLayout";

export function IntelligencePage() {
  const { t } = useTranslation("intelligence");
const { t: tRoutes } = useTranslation("routes");

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: tRoutes("intelligence.label") }]}
        eyebrow={t("page.eyebrow")}
        title={t("page.title")}
        description={t("page.description")}
      />

      <RiskSignalFeed />

      <ProspectGapTable />

      <CustomerBuyingBehaviorCard />

      <CategoryTrendRadar />

      <RevenueDiagnosisCard />

      <ProductPerformanceCard />

      <AffinityMatrix />

      <SectionCard
        title={t("page.workspaceTitle")}
        description={t("page.workspaceDescription")}
      >
        <SurfaceMessage>
          {t("page.placeholder")}
        </SurfaceMessage>
      </SectionCard>
    </div>
  );
}