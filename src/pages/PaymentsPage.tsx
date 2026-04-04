import ReconciliationScreen from "../domain/payments/components/ReconciliationScreen";
import { PageHeader, SectionCard } from "../components/layout/PageLayout";

export function PaymentsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Payments"
        title="Payments"
        description="Reconcile inbound payments, confirm system suggestions, and manually resolve remaining exceptions."
      />

      <SectionCard title="Reconciliation Workspace" description="Operational matching workflow for open inbound payments.">
        <ReconciliationScreen />
      </SectionCard>
    </div>
  );
}