import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { PageHeader, SectionCard, SurfaceMessage } from "../../components/layout/PageLayout";
import { Button } from "../../components/ui/button";
import { Field, FieldLabel } from "../../components/ui/field";
import { Input } from "../../components/ui/input";
import { useCRMSetupBundle } from "../../domain/crm/hooks/useCRMSetupBundle";
import type {
  CRMPipelineDrilldownGroup,
  CRMPipelineReport,
  CRMPipelineReportParams,
  CRMPipelineSegment,
} from "../../domain/crm/types";
import { getCRMPipelineReport } from "../../lib/api/crm";
import { SELECT_CLASS_NAME } from "../../lib/constants";
import { CRM_REPORTING_ROUTE, type AppRoute } from "../../lib/routes";

const DEFAULT_FILTERS: CRMPipelineReportParams = {
  record_type: "all",
  scope: "open",
  start_date: "",
  end_date: "",
  compare_start_date: "",
  compare_end_date: "",
  sales_stage: "",
  territory: "",
  customer_group: "",
  status: "",
  owner: "",
  lost_reason: "",
  utm_source: "",
  utm_medium: "",
  utm_campaign: "",
  utm_content: "",
};

function SummaryCard({
  label,
  value,
  onClick,
  selected = false,
}: {
  label: string;
  value: string | number;
  onClick?: () => void;
  selected?: boolean;
}) {
  const content = (
    <>
      <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-foreground">{value}</p>
    </>
  );

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={`rounded-xl border p-4 text-left transition-colors ${selected ? "border-ring bg-accent/40" : "border-border/70 bg-background/50 hover:border-ring/70"}`}
      >
        {content}
      </button>
    );
  }

  return (
    <div className="rounded-xl border border-border/70 bg-background/50 p-4">
      {content}
    </div>
  );
}

function SegmentGroup({ title, items }: { title: string; items: CRMPipelineSegment[] }) {
  const { t } = useTranslation("common");
  const showOrderedRevenue = items.some((segment) => Number(segment.ordered_revenue ?? 0) > 0);

  return (
    <SectionCard title={title}>
      <div className="space-y-3">
        {items.length ? (
          items.map((segment) => (
            <div
              key={`${segment.record_type ?? "all"}-${segment.key}`}
              className={`grid gap-2 rounded-xl border border-border/70 bg-background/40 p-4 md:items-center ${showOrderedRevenue ? "md:grid-cols-[minmax(0,1fr)_120px_140px_160px]" : "md:grid-cols-[minmax(0,1fr)_120px_140px]"}`}
            >
              <div>
                <p className="font-medium text-foreground">{segment.label}</p>
                <p className="text-sm text-muted-foreground">{segment.record_type ?? t("crm.reporting.recordTypeAll")}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.reporting.count")}</p>
                <p className="text-sm font-medium text-foreground">{segment.count}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.reporting.amount")}</p>
                <p className="text-sm font-medium text-foreground">{segment.amount}</p>
              </div>
              {showOrderedRevenue ? (
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.reporting.orderedRevenue")}</p>
                  <p className="text-sm font-medium text-foreground">{segment.ordered_revenue ?? "0.00"}</p>
                </div>
              ) : null}
            </div>
          ))
        ) : (
          <SurfaceMessage>{t("crm.reporting.noMatches")}</SurfaceMessage>
        )}
      </div>
    </SectionCard>
  );
}

export default function CRMPipelineReportPage() {
  const { t } = useTranslation("common");
  const { t: tRoutes } = useTranslation("routes");
  const { territoryOptions, customerGroupOptions, salesStageOptions } = useCRMSetupBundle();
  const [filters, setFilters] = useState<CRMPipelineReportParams>(DEFAULT_FILTERS);
  const [report, setReport] = useState<CRMPipelineReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeDrilldown, setActiveDrilldown] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getCRMPipelineReport(filters)
      .then((result) => {
        if (!cancelled) {
          setReport(result);
        }
      })
      .catch((caughtError) => {
        if (!cancelled) {
          setError(caughtError instanceof Error ? caughtError.message : t("crm.reporting.loadError"));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [filters, t]);

  useEffect(() => {
    if (!report) {
      return;
    }
    if (!report.analytics.drilldowns.some((group) => group.key === activeDrilldown)) {
      setActiveDrilldown(report.analytics.drilldowns[0]?.key ?? "");
    }
  }, [activeDrilldown, report]);

  /**
   * Mapping of segment group keys to their source report properties.
   * This centralized mapping makes it easy to add/remove groups and ensures consistency.
   */
  const SEGMENT_GROUP_MAPPINGS = {
    status: "by_status",
    salesStage: "by_sales_stage",
    territory: "by_territory",
    customerGroup: "by_customer_group",
    owner: "by_owner",
    lostReason: "by_lost_reason",
    utmSource: "by_utm_source",
    utmMedium: "by_utm_medium",
    utmCampaign: "by_utm_campaign",
    utmContent: "by_utm_content",
    conversionPath: "by_conversion_path",
    conversionSource: "by_conversion_source",
  } as const;

  type GroupKey = keyof typeof SEGMENT_GROUP_MAPPINGS;

  const groups = useMemo(() => {
    if (!report) {
      // Return empty arrays for all groups when report is not loaded
      return Object.fromEntries(
        Object.keys(SEGMENT_GROUP_MAPPINGS).map((key) => [key, [] as CRMPipelineSegment[]])
      ) as Record<GroupKey, CRMPipelineSegment[]>;
    }

    // Map each group key to its source property from the report
    return Object.fromEntries(
      Object.entries(SEGMENT_GROUP_MAPPINGS).map(([groupKey, reportProp]) => [
        groupKey,
        (report as Record<string, CRMPipelineSegment[] | undefined>)[reportProp] ?? [],
      ])
    ) as Record<GroupKey, CRMPipelineSegment[]>;
  }, [report]);

  const activeDrilldownGroup: CRMPipelineDrilldownGroup | null = useMemo(() => {
    if (!report) {
      return null;
    }
    return report.analytics.drilldowns.find((group) => group.key === activeDrilldown) ?? null;
  }, [activeDrilldown, report]);

  const comparisonCards = report
    ? [
        ["open_pipeline_value", t("crm.reporting.openPipelineValue")],
        ["win_rate", t("crm.reporting.winRate")],
        ["lead_conversion_rate", t("crm.reporting.leadConversionRate")],
        ["converted_revenue", t("crm.reporting.convertedRevenue")],
      ]
    : [];

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: tRoutes("crmReporting.label"), href: CRM_REPORTING_ROUTE as AppRoute }]}
        eyebrow={t("crm.reporting.eyebrow")}
        title={t("crm.reporting.title")}
        description={t("crm.reporting.description")}
      />

      <SectionCard title={t("crm.reporting.filtersTitle")} description={t("crm.reporting.filtersDescription")}>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Field>
            <FieldLabel htmlFor="record_type">{t("crm.reporting.recordType")}</FieldLabel>
            <select
              id="record_type"
              className={SELECT_CLASS_NAME}
              value={filters.record_type}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  record_type: event.target.value as CRMPipelineReportParams["record_type"],
                }))
              }
            >
              <option value="all">{t("crm.reporting.recordTypeAll")}</option>
              <option value="lead">{t("crm.reporting.recordTypeLead")}</option>
              <option value="opportunity">{t("crm.reporting.recordTypeOpportunity")}</option>
              <option value="quotation">{t("crm.reporting.recordTypeQuotation")}</option>
            </select>
          </Field>
          <Field>
            <FieldLabel htmlFor="scope">{t("crm.reporting.scope")}</FieldLabel>
            <select
              id="scope"
              className={SELECT_CLASS_NAME}
              value={filters.scope}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  scope: event.target.value as CRMPipelineReportParams["scope"],
                }))
              }
            >
              <option value="open">{t("crm.reporting.scopeActive")}</option>
              <option value="all">{t("crm.reporting.scopeAll")}</option>
              <option value="terminal">{t("crm.reporting.scopeTerminal")}</option>
            </select>
          </Field>
          <Field>
            <FieldLabel htmlFor="sales_stage">{t("crm.reporting.salesStage")}</FieldLabel>
            <select
              id="sales_stage"
              className={SELECT_CLASS_NAME}
              value={filters.sales_stage ?? ""}
              onChange={(event) => setFilters((current) => ({ ...current, sales_stage: event.target.value }))}
            >
              <option value="">{t("crm.setup.selectPlaceholder")}</option>
              {salesStageOptions.map((option) => (
                <option key={option.id} value={option.name}>{option.name}</option>
              ))}
            </select>
          </Field>
          <Field>
            <FieldLabel htmlFor="territory">{t("crm.reporting.territory")}</FieldLabel>
            <select
              id="territory"
              className={SELECT_CLASS_NAME}
              value={filters.territory ?? ""}
              onChange={(event) => setFilters((current) => ({ ...current, territory: event.target.value }))}
            >
              <option value="">{t("crm.setup.selectPlaceholder")}</option>
              {territoryOptions.map((option) => (
                <option key={option.id} value={option.name}>{option.name}</option>
              ))}
            </select>
          </Field>
          <Field>
            <FieldLabel htmlFor="customer_group">{t("crm.reporting.customerGroup")}</FieldLabel>
            <select
              id="customer_group"
              className={SELECT_CLASS_NAME}
              value={filters.customer_group ?? ""}
              onChange={(event) => setFilters((current) => ({ ...current, customer_group: event.target.value }))}
            >
              <option value="">{t("crm.setup.selectPlaceholder")}</option>
              {customerGroupOptions.map((option) => (
                <option key={option.id} value={option.name}>{option.name}</option>
              ))}
            </select>
          </Field>
          <Field>
            <FieldLabel htmlFor="start_date">{t("crm.reporting.periodStart")}</FieldLabel>
            <Input id="start_date" type="date" value={filters.start_date ?? ""} onChange={(event) => setFilters((current) => ({ ...current, start_date: event.target.value }))} />
          </Field>
          <Field>
            <FieldLabel htmlFor="end_date">{t("crm.reporting.periodEnd")}</FieldLabel>
            <Input id="end_date" type="date" value={filters.end_date ?? ""} onChange={(event) => setFilters((current) => ({ ...current, end_date: event.target.value }))} />
          </Field>
          <Field>
            <FieldLabel htmlFor="compare_start_date">{t("crm.reporting.compareStart")}</FieldLabel>
            <Input id="compare_start_date" type="date" value={filters.compare_start_date ?? ""} onChange={(event) => setFilters((current) => ({ ...current, compare_start_date: event.target.value }))} />
          </Field>
          <Field>
            <FieldLabel htmlFor="compare_end_date">{t("crm.reporting.compareEnd")}</FieldLabel>
            <Input id="compare_end_date" type="date" value={filters.compare_end_date ?? ""} onChange={(event) => setFilters((current) => ({ ...current, compare_end_date: event.target.value }))} />
          </Field>
          <Field>
            <FieldLabel htmlFor="status">{t("crm.reporting.status")}</FieldLabel>
            <Input id="status" value={filters.status ?? ""} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))} />
          </Field>
          <Field>
            <FieldLabel htmlFor="owner">{t("crm.reporting.owner")}</FieldLabel>
            <Input id="owner" value={filters.owner ?? ""} onChange={(event) => setFilters((current) => ({ ...current, owner: event.target.value }))} />
          </Field>
          <Field>
            <FieldLabel htmlFor="utm_source">{t("crm.reporting.utmSource")}</FieldLabel>
            <Input id="utm_source" value={filters.utm_source ?? ""} onChange={(event) => setFilters((current) => ({ ...current, utm_source: event.target.value }))} />
          </Field>
          <Field>
            <FieldLabel htmlFor="utm_medium">{t("crm.reporting.utmMedium")}</FieldLabel>
            <Input id="utm_medium" value={filters.utm_medium ?? ""} onChange={(event) => setFilters((current) => ({ ...current, utm_medium: event.target.value }))} />
          </Field>
          <Field>
            <FieldLabel htmlFor="utm_campaign">{t("crm.reporting.utmCampaign")}</FieldLabel>
            <Input id="utm_campaign" value={filters.utm_campaign ?? ""} onChange={(event) => setFilters((current) => ({ ...current, utm_campaign: event.target.value }))} />
          </Field>
          <Field>
            <FieldLabel htmlFor="utm_content">{t("crm.reporting.utmContent")}</FieldLabel>
            <Input id="utm_content" value={filters.utm_content ?? ""} onChange={(event) => setFilters((current) => ({ ...current, utm_content: event.target.value }))} />
          </Field>
          <Field>
            <FieldLabel htmlFor="lost_reason">{t("crm.reporting.lostReason")}</FieldLabel>
            <Input id="lost_reason" value={filters.lost_reason ?? ""} onChange={(event) => setFilters((current) => ({ ...current, lost_reason: event.target.value }))} />
          </Field>
        </div>
        <div className="mt-4 flex justify-end">
          <Button type="button" variant="outline" onClick={() => setFilters(DEFAULT_FILTERS)}>
            {t("crm.reporting.resetFilters")}
          </Button>
        </div>
      </SectionCard>

      {error ? <SurfaceMessage tone="warning">{error}</SurfaceMessage> : null}
      {loading ? <SurfaceMessage>{t("crm.reporting.loading")}</SurfaceMessage> : null}

      {report ? (
        <>
          <SectionCard title={t("crm.reporting.analyticsTitle")} description={t("crm.reporting.analyticsDescription")}>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <SummaryCard
                label={t("crm.reporting.openPipelineValue")}
                value={report.analytics.kpis.open_pipeline_value}
                onClick={() => setActiveDrilldown("open_pipeline")}
                selected={activeDrilldown === "open_pipeline"}
              />
              <SummaryCard
                label={t("crm.reporting.weightedPipelineValue")}
                value={report.analytics.kpis.weighted_pipeline_value}
                onClick={() => setActiveDrilldown("open_pipeline")}
                selected={activeDrilldown === "open_pipeline"}
              />
              <SummaryCard
                label={t("crm.reporting.winRate")}
                value={`${report.analytics.kpis.win_rate}%`}
                onClick={() => setActiveDrilldown("terminal_outcomes")}
                selected={activeDrilldown === "terminal_outcomes"}
              />
              <SummaryCard
                label={t("crm.reporting.leadConversionRate")}
                value={`${report.analytics.kpis.lead_conversion_rate}%`}
                onClick={() => setActiveDrilldown("qualified_leads")}
                selected={activeDrilldown === "qualified_leads"}
              />
              <SummaryCard
                label={t("crm.reporting.averageDealSize")}
                value={report.analytics.kpis.average_deal_size}
                onClick={() => setActiveDrilldown("converted_orders")}
                selected={activeDrilldown === "converted_orders"}
              />
              <SummaryCard
                label={t("crm.reporting.convertedRevenue")}
                value={report.analytics.kpis.converted_revenue}
                onClick={() => setActiveDrilldown("converted_orders")}
                selected={activeDrilldown === "converted_orders"}
              />
              <SummaryCard
                label={t("crm.reporting.timeToConversion")}
                value={report.analytics.kpis.time_to_conversion}
                onClick={() => setActiveDrilldown("qualified_leads")}
                selected={activeDrilldown === "qualified_leads"}
              />
            </div>
          </SectionCard>

          <SectionCard title={t("crm.reporting.comparisonTitle")} description={t("crm.reporting.comparisonDescription")}>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {comparisonCards.map(([key, label]) => {
                const metric = report.analytics.comparison[key] ?? { current_value: "0.00", previous_value: "0.00", delta: "0.00" };
                return (
                  <div key={key} className="rounded-xl border border-border/70 bg-background/50 p-4">
                    <p className="text-sm font-medium text-foreground">{label}</p>
                    <div className="mt-3 space-y-2 text-sm text-muted-foreground">
                      <p>{t("crm.reporting.currentPeriod")}: {metric.current_value}</p>
                      <p>{t("crm.reporting.previousPeriod")}: {metric.previous_value}</p>
                      <p>{t("crm.reporting.delta")}: {metric.delta}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </SectionCard>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <SummaryCard label={t("crm.reporting.leadCount")} value={report.totals.lead_count} />
            <SummaryCard label={t("crm.reporting.opportunityCount")} value={report.totals.opportunity_count} />
            <SummaryCard label={t("crm.reporting.quotationCount")} value={report.totals.quotation_count} />
            <SummaryCard label={t("crm.reporting.openCount")} value={report.totals.open_count} />
            <SummaryCard label={t("crm.reporting.terminalCount")} value={report.totals.terminal_count} />
            <SummaryCard label={t("crm.reporting.openAmount")} value={report.totals.open_pipeline_amount} />
            <SummaryCard label={t("crm.reporting.terminalAmount")} value={report.totals.terminal_pipeline_amount} />
            <SummaryCard label={t("crm.reporting.orderedRevenue")} value={report.totals.ordered_revenue ?? "0.00"} />
            <SummaryCard label={t("crm.reporting.conversionCount")} value={report.totals.conversion_count ?? 0} />
            <SummaryCard label={t("crm.reporting.avgDaysToConversion")} value={report.totals.avg_days_to_conversion ?? "0.00"} />
          </div>

          <SectionCard title={t("crm.reporting.funnelTitle")} description={t("crm.reporting.funnelDescription")}>
            <div className="space-y-3">
              {report.analytics.funnel.map((stage) => {
                const drilldownKey = stage.key === "converted" ? "converted_orders" : stage.key === "opportunity" ? "open_pipeline" : "qualified_leads";
                return (
                  <button
                    key={stage.key}
                    type="button"
                    onClick={() => setActiveDrilldown(drilldownKey)}
                    className="grid w-full gap-3 rounded-xl border border-border/70 bg-background/40 p-4 text-left md:grid-cols-[minmax(0,1fr)_120px_140px_160px]"
                  >
                    <div>
                      <p className="font-medium text-foreground">{t(`crm.reporting.funnelStage.${stage.key}`)}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.reporting.count")}</p>
                      <p className="text-sm font-medium text-foreground">{stage.count}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.reporting.dropoffCount")}</p>
                      <p className="text-sm font-medium text-foreground">{stage.dropoff_count}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.reporting.conversionRate")}</p>
                      <p className="text-sm font-medium text-foreground">{stage.conversion_rate}%</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </SectionCard>

          <SectionCard title={t("crm.reporting.dropOffTitle")} description={t("crm.reporting.dropOffDescription")}>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <SummaryCard label={t("crm.reporting.dropOffLeadOnly")} value={report.dropoff.lead_only_count} />
              <SummaryCard label={t("crm.reporting.dropOffOpportunityWithoutQuotation")} value={report.dropoff.opportunity_without_quotation_count} />
              <SummaryCard label={t("crm.reporting.dropOffQuotationWithoutOrder")} value={report.dropoff.quotation_without_order_count} />
              <SummaryCard label={t("crm.reporting.dropOffQuotationWithOrder")} value={report.dropoff.quotation_with_order_count} />
            </div>
          </SectionCard>

          <SectionCard title={t("crm.reporting.terminalAnalysisTitle")} description={t("crm.reporting.terminalAnalysisDescription")}>
            <div className="grid gap-6 xl:grid-cols-3">
              <SegmentGroup title={t("crm.reporting.byStatusTitle")} items={report.analytics.terminal_by_status} />
              <SegmentGroup title={t("crm.reporting.byLostReasonTitle")} items={report.analytics.terminal_by_lost_reason} />
              <SegmentGroup title={t("crm.reporting.byCompetitorTitle")} items={report.analytics.terminal_by_competitor} />
            </div>
          </SectionCard>

          <SectionCard title={t("crm.reporting.repPerformanceTitle")} description={t("crm.reporting.repPerformanceDescription")}>
            <div className="space-y-3">
              {report.analytics.owner_scorecards.length ? (
                report.analytics.owner_scorecards.map((scorecard) => (
                  <div key={scorecard.owner} className="grid gap-3 rounded-xl border border-border/70 bg-background/40 p-4 md:grid-cols-[minmax(0,1fr)_120px_120px_140px_140px_140px_140px]">
                    <div>
                      <p className="font-medium text-foreground">{scorecard.owner}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.reporting.assignedLeads")}</p>
                      <p className="text-sm font-medium text-foreground">{scorecard.assigned_leads}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.reporting.ownedOpportunities")}</p>
                      <p className="text-sm font-medium text-foreground">{scorecard.owned_opportunities}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.reporting.openPipelineValue")}</p>
                      <p className="text-sm font-medium text-foreground">{scorecard.open_pipeline_value}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.reporting.weightedForecast")}</p>
                      <p className="text-sm font-medium text-foreground">{scorecard.weighted_pipeline_value}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.reporting.convertedRevenue")}</p>
                      <p className="text-sm font-medium text-foreground">{scorecard.converted_revenue}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.reporting.timeToConversion")}</p>
                      <p className="text-sm font-medium text-foreground">{scorecard.time_to_conversion}</p>
                    </div>
                  </div>
                ))
              ) : (
                <SurfaceMessage>{t("crm.reporting.noMatches")}</SurfaceMessage>
              )}
            </div>
          </SectionCard>

          <SectionCard title={t("crm.reporting.drilldownTitle")} description={t("crm.reporting.drilldownDescription")}>
            {activeDrilldownGroup ? (
              <div className="space-y-3">
                <p className="text-sm font-medium text-foreground">{activeDrilldownGroup.label}</p>
                {activeDrilldownGroup.records.length ? (
                  activeDrilldownGroup.records.map((record) => (
                    <div key={`${record.record_type}-${record.record_id}`} className="grid gap-3 rounded-xl border border-border/70 bg-background/40 p-4 md:grid-cols-[minmax(0,1fr)_120px_140px_120px_140px]">
                      <div>
                        <p className="font-medium text-foreground">{record.label}</p>
                        <p className="text-sm text-muted-foreground">{record.record_id}</p>
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.reporting.drilldownRecordType")}</p>
                        <p className="text-sm font-medium text-foreground">{record.record_type}</p>
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.reporting.drilldownStatus")}</p>
                        <p className="text-sm font-medium text-foreground">{record.status}</p>
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.reporting.drilldownOwner")}</p>
                        <p className="text-sm font-medium text-foreground">{record.owner || "-"}</p>
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.reporting.drilldownAmount")}</p>
                        <p className="text-sm font-medium text-foreground">{record.amount}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <SurfaceMessage>{t("crm.reporting.drilldownEmpty")}</SurfaceMessage>
                )}
              </div>
            ) : (
              <SurfaceMessage>{t("crm.reporting.drilldownEmpty")}</SurfaceMessage>
            )}
          </SectionCard>

          <SegmentGroup title={t("crm.reporting.byStatusTitle")} items={groups.status} />
          <SegmentGroup title={t("crm.reporting.bySalesStageTitle")} items={groups.salesStage} />
          <SegmentGroup title={t("crm.reporting.byTerritoryTitle")} items={groups.territory} />
          <SegmentGroup title={t("crm.reporting.byCustomerGroupTitle")} items={groups.customerGroup} />
          <SegmentGroup title={t("crm.reporting.byOwnerTitle")} items={groups.owner} />
          <SegmentGroup title={t("crm.reporting.byLostReasonTitle")} items={groups.lostReason} />
          <SegmentGroup title={t("crm.reporting.byUtmSourceTitle")} items={groups.utmSource} />
          <SegmentGroup title={t("crm.reporting.byUtmMediumTitle")} items={groups.utmMedium} />
          <SegmentGroup title={t("crm.reporting.byUtmCampaignTitle")} items={groups.utmCampaign} />
          <SegmentGroup title={t("crm.reporting.byUtmContentTitle")} items={groups.utmContent} />
          <SegmentGroup title={t("crm.reporting.byConversionPathTitle")} items={groups.conversionPath} />
          <SegmentGroup title={t("crm.reporting.byConversionSourceTitle")} items={groups.conversionSource} />
        </>
      ) : null}
    </div>
  );
}
