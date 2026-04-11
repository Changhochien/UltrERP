import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useTranslation } from "react-i18next";

interface MonthlyDemandChartProps {
  data: { month: string; total_qty: number }[];
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: { month: string; total_qty: number } }>;
}) {
  const { t } = useTranslation("common", {
    keyPrefix: "inventory.productDetail.analyticsTab.monthlyDemand",
  });

  if (!active || !payload || payload.length === 0) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-xl border border-border bg-background px-3 py-2 shadow-lg">
      <p className="text-xs font-medium text-muted-foreground">{p.month}</p>
      <p className="text-sm font-semibold">{t("tooltipUnits", { count: p.total_qty })}</p>
    </div>
  );
}

export function MonthlyDemandChart({ data }: MonthlyDemandChartProps) {
  const { t } = useTranslation("common", {
    keyPrefix: "inventory.productDetail.analyticsTab.monthlyDemand",
  });

  if (data.length === 0) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-muted-foreground">
        <p className="text-sm">{t("empty")}</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis
          dataKey="month"
          tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          tickLine={false}
          axisLine={{ stroke: "var(--border)" }}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          tickLine={false}
          axisLine={false}
          width={40}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="total_qty" fill="#3b82f6" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
