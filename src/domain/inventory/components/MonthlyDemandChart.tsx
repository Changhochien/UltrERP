import { ParentSize } from "@visx/responsive";
import { scaleBand, scaleLinear } from "@visx/scale";
import { Bar } from "@visx/shape";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { Group } from "@visx/group";
import { TooltipWithBounds, useTooltip } from "@visx/tooltip";

interface MonthlyDemandChartProps {
  data: { month: string; total_qty: number }[];
}

function ChartInner({
  data,
  width,
  height,
}: {
  data: { month: string; total_qty: number }[];
  width: number;
  height: number;
}) {
  const { showTooltip, hideTooltip, tooltipOpen, tooltipData, tooltipLeft, tooltipTop } =
    useTooltip<{ month: string; total_qty: number }>();

  const margin = { top: 10, right: 10, left: 40, bottom: 40 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const xScale = scaleBand({
    domain: data.map((d) => d.month),
    range: [0, innerWidth],
    padding: 0.3,
  });

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
          {data.map((d, i) => {
            const barHeight = innerHeight - (yScale(d.total_qty) ?? 0);
            const barX = xScale(d.month) ?? 0;
            const barY = yScale(d.total_qty) ?? 0;
            return (
              <Bar
                key={i}
                x={barX}
                y={barY}
                width={xScale.bandwidth()}
                height={barHeight}
                fill="#3b82f6"
                rx={4}
                onMouseEnter={(e) => {
                  showTooltip({
                    tooltipData: d,
                    tooltipLeft: e.clientX,
                    tooltipTop: e.clientY,
                  });
                }}
                onMouseLeave={hideTooltip}
              />
            );
          })}
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
          <p className="text-sm font-semibold">{tooltipData.total_qty} units</p>
        </TooltipWithBounds>
      )}
    </div>
  );
}

export function MonthlyDemandChart({ data }: MonthlyDemandChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-muted-foreground">
        <p className="text-sm">No demand data available</p>
      </div>
    );
  }

  return (
    <ParentSize>
      {({ width }) => <ChartInner data={data} width={width} height={260} />}
    </ParentSize>
  );
}
