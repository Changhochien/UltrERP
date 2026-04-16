import { useTranslation } from "react-i18next";

import { AffinityMatrix } from "../domain/intelligence/components/AffinityMatrix";
import { CategoryTrendRadar } from "../domain/intelligence/components/CategoryTrendRadar";
import { ProspectGapTable } from "../domain/intelligence/components/ProspectGapTable";
import { ProductPerformanceCard } from "../domain/intelligence/components/ProductPerformanceCard";
import { RevenueDiagnosisCard } from "../domain/intelligence/components/RevenueDiagnosisCard";
import { RiskSignalFeed } from "../domain/intelligence/components/RiskSignalFeed";
import { PageHeader, SectionCard, SurfaceMessage } from "../components/layout/PageLayout";

export function IntelligencePage() {
  const { t } = useTranslation("common");

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("intelligence.page.eyebrow")}
        title={t("intelligence.page.title")}
        description={t("intelligence.page.description")}
      />

      <RiskSignalFeed />

      <ProspectGapTable />

      <CategoryTrendRadar />

      <RevenueDiagnosisCard />

      <ProductPerformanceCard />

      <AffinityMatrix />

      <SectionCard
        title={t("intelligence.page.workspaceTitle")}
        description={t("intelligence.page.workspaceDescription")}
      >
        <SurfaceMessage>
          {t("intelligence.page.placeholder")}
        </SurfaceMessage>
      </SectionCard>
    </div>
  );
}