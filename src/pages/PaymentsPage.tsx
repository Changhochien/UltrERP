import ReconciliationScreen from "../domain/payments/components/ReconciliationScreen";

export function PaymentsPage() {
  return (
    <section className="hero-card" style={{ width: "min(72rem, 100%)" }}>
      <h1 style={{ fontSize: "2rem", lineHeight: 1.1 }}>Payments</h1>
      <p className="caption">Reconcile inbound payments and resolve suggested matches.</p>

      <div style={{ marginTop: "1.5rem" }}>
        <ReconciliationScreen />
      </div>
    </section>
  );
}