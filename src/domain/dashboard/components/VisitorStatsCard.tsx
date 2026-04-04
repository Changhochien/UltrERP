/** Visitor statistics dashboard card with PostHog data. */

import { useVisitorStats } from "../hooks/useDashboard";

export function VisitorStatsCard() {
  const { data, isLoading, error } = useVisitorStats();

  if (isLoading) {
    return (
      <div className="kpi-card" data-testid="visitor-stats-card">
        <h3>Visitor Stats</h3>
        <div data-testid="visitor-stats-loading">
          <div className="skeleton" style={{ height: "4rem" }} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="kpi-card" data-testid="visitor-stats-card">
        <h3>Visitor Stats</h3>
        <p className="error-text">Analytics unavailable</p>
      </div>
    );
  }

  if (!data) return null;

  if (!data.is_configured) {
    return (
      <div className="kpi-card" data-testid="visitor-stats-card">
        <h3>Visitor Stats</h3>
        <p className="muted-text" data-testid="visitor-not-configured">
          Analytics not configured
        </p>
      </div>
    );
  }

  if (data.error) {
    return (
      <div className="kpi-card" data-testid="visitor-stats-card">
        <h3>Visitor Stats</h3>
        <p className="error-text">Analytics unavailable</p>
      </div>
    );
  }

  return (
    <div className="kpi-card" data-testid="visitor-stats-card">
      <h3>Visitor Stats</h3>
      <p className="date-label" data-testid="visitor-date">
        Yesterday ({data.date})
      </p>
      <div className="visitor-metrics">
        <div className="metric">
          <span className="metric-value" data-testid="visitor-count" aria-label={`Unique visitors: ${data.visitor_count}`}>
            {data.visitor_count.toLocaleString()}
          </span>
          <span className="metric-label">Unique Visitors</span>
        </div>
        <div className="metric">
          <span className="metric-value" data-testid="inquiry-count" aria-label={`Inquiries: ${data.inquiry_count}`}>
            {data.inquiry_count.toLocaleString()}
          </span>
          <span className="metric-label">Inquiries</span>
        </div>
        <div className="metric">
          <span
            className="metric-value"
            data-testid="conversion-rate"
            aria-label={`Conversion rate: ${data.conversion_rate != null ? `${data.conversion_rate}%` : "not available"}`}
          >
            {data.conversion_rate != null ? `${data.conversion_rate}%` : "—"}
          </span>
          <span className="metric-label">Conversion</span>
        </div>
      </div>
    </div>
  );
}
