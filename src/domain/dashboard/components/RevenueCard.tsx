/** Revenue comparison card — today vs yesterday. */

import type { RevenueSummary } from "../types";

function formatTWD(value: string): string {
  return `NT$ ${Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

interface RevenueCardProps {
  data: RevenueSummary | null;
  isLoading: boolean;
  error: string | null;
}

export function RevenueCard({ data, isLoading, error }: RevenueCardProps) {
  if (isLoading) {
    return (
      <div className="kpi-card" data-testid="revenue-card-loading">
        <h3>Revenue Comparison</h3>
        <div className="skeleton" style={{ height: "6rem" }} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="kpi-card kpi-card--error" data-testid="revenue-card-error">
        <h3>Revenue Comparison</h3>
        <p>{error}</p>
      </div>
    );
  }

  if (!data) return null;

  const changePercent = data.change_percent;
  let changeDisplay: string;
  let changeClass = "";

  if (changePercent === null) {
    changeDisplay = "—";
  } else {
    const pct = Number(changePercent);
    if (pct > 0) {
      changeDisplay = `▲ +${pct.toFixed(1)}%`;
      changeClass = "change--positive";
    } else if (pct < 0) {
      changeDisplay = `▼ ${pct.toFixed(1)}%`;
      changeClass = "change--negative";
    } else {
      changeDisplay = "0.0%";
    }
  }

  return (
    <div className="kpi-card" data-testid="revenue-card">
      <h3>Revenue Comparison</h3>
      <div className="kpi-row">
        <div>
          <span className="kpi-label">Today ({data.today_date})</span>
          <span className="kpi-value">{formatTWD(data.today_revenue)}</span>
        </div>
        <div>
          <span className="kpi-label">Yesterday ({data.yesterday_date})</span>
          <span className="kpi-value">{formatTWD(data.yesterday_revenue)}</span>
        </div>
      </div>
      <div
        className={`kpi-change ${changeClass}`}
        data-testid="change-indicator"
        aria-label={
          changePercent === null
            ? "No change data available"
            : `Revenue change: ${changeDisplay}`
        }
      >
        {changeDisplay}
      </div>
    </div>
  );
}
