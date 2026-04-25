import { ParentSize } from "@visx/responsive";
import { scaleBand, scaleLinear } from "@visx/scale";
import { Bar, LinePath } from "@visx/shape";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { Group } from "@visx/group";
import { curveMonotoneX } from "@visx/curve";
import { TooltipWithBounds, useTooltip } from "@visx/tooltip";
import { useTranslation } from "react-i18next";

interface MonthlyDemandChartProps {
  data: { month: string; total_qty: number }[];
  variant?: "bar" | "line";
}

function getVisibleTickMonths(months: string[], innerWidth: number) {
  const maxTickCount = Math.max(2, Math.floor(innerWidth / 72));
  const step = Math.max(1, Math.ceil(months.length / maxTickCount));
  return months.filter((_month, index) => index % step === 0 || index === months.length - 1);
}

function ChartInner({
  data,
  variant,
  width,
  height,
}: {
  data: { month: string; total_qty: number }[];
  variant: "bar" | "line";
  width: number;
  height: number;
}) {
  const { t } = useTranslation("common", {
    keyPrefix: "inventory.productDetail.analyticsTab.monthlyDemand",
  });
  const { showTooltip, hideTooltip, tooltipOpen, tooltipData, tooltipLeft, tooltipTop } =
    useTooltip<{ month: string; total_qty: number }>();

  const margin = { top: 10, right: 10, left: 40, bottom: 40 };
  const innerWidth = Math.max(0, width - margin.left - margin.right);
  const innerHeight = Math.max(0, height - margin.top - margin.bottom);

  if (!data.length || innerWidth <= 0 || innerHeight <= 0) {
    return null;
  }

  const xScale = scaleBand({
    domain: data.map((d) => d.month),
    range: [0, innerWidth],
    padding: 0.3,
  });
  const tickMonths = getVisibleTickMonths(data.map((d) => d.month), innerWidth);

  const yMax = Math.max(...data.map((d) => d.total_qty), 1);
  const yScale = scaleLinear({
    domain: [0, yMax * 1.1],
    range: [innerHeight, 0],
  });

  return (
    <div style={{ position: "relative" }}>
      <svg width={width} height={height}>
        <Group left={margin.left} top={margin.top}>
          <GridRows
            scale={yScale}
            width={innerWidth}
            stroke="var(--border)"
            strokeDasharray="3 3"
          />
          <AxisBottom
            top={innerHeight}
            scale={xScale}
            tickValues={tickMonths}
            tickLabelProps={() => ({
              fill: "var(--muted-foreground)",
              fontSize: 11,
              textAnchor: "middle",
            })}
            stroke="var(--border)"
          />
          <AxisLeft
            scale={yScale}
            tickLabelProps={() => ({
              fill: "var(--muted-foreground)",
              fontSize: 11,
              textAnchor: "end",
            })}
            stroke="var(--border)"
          />
          {variant === "line" ? (
            <>
              <LinePath
                data={data}
                x={(d) => (xScale(d.month) ?? 0) + xScale.bandwidth() / 2}
                y={(d) => yScale(d.total_qty) ?? 0}
                stroke="#3b82f6"
                strokeWidth={2.5}
                curve={curveMonotoneX}
              />
              {data.map((d, i) => {
                const cx = (xScale(d.month) ?? 0) + xScale.bandwidth() / 2;
                const cy = yScale(d.total_qty) ?? 0;
                return (
                  <circle
                    key={i}
                    cx={cx}
                    cy={cy}
                    r={4}
                    fill="#3b82f6"
                    stroke="white"
                    strokeWidth={1.5}
                    onMouseEnter={(e) => {
                      showTooltip({
                        tooltipData: d,
                        tooltipLeft: e.pageX,
                        tooltipTop: e.pageY,
                      });
                    }}
                    onMouseLeave={hideTooltip}
                  />
                );
              })}
            </>
          ) : (
            data.map((d, i) => {
              const rawBarHeight = innerHeight - (yScale(d.total_qty) ?? 0);
              const barHeight = Math.max(0, rawBarHeight);
              const barX = xScale(d.month) ?? 0;
              const barY = yScale(d.total_qty) ?? 0;
              const barWidth = Math.max(0, xScale.bandwidth());
              return (
                <Bar
                  key={i}
                  x={barX}
                  y={barY}
                  width={barWidth}
                  height={barHeight}
                  fill="#3b82f6"
                  rx={4}
                  onMouseEnter={(e) => {
                    showTooltip({
                      tooltipData: d,
                      tooltipLeft: e.pageX,
                      tooltipTop: e.pageY,
                    });
                  }}
                  onMouseLeave={hideTooltip}
                />
              );
            })
          )}
        </Group>
      </svg>
      {tooltipOpen && tooltipData && (
        <TooltipWithBounds
          left={tooltipLeft ?? 0}
          top={tooltipTop ?? 0}
          style={{
            background: "var(--background)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            padding: "8px 12px",
            fontSize: 12,
            position: "fixed",
          }}
        >
          <p className="text-xs font-medium text-muted-foreground">{tooltipData.month}</p>
          <p className="text-sm font-semibold">
            {t("tooltipUnits", { count: tooltipData.total_qty })}
          </p>
        </TooltipWithBounds>
      )}
    </div>
  );
}

export function MonthlyDemandChart({ data, variant = "bar" }: MonthlyDemandChartProps) {
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
    <ParentSize>
      {({ width }) => <ChartInner data={data} variant={variant} width={width} height={260} />}
    </ParentSize>
  );
}
