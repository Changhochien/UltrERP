import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { PageHeader, SectionCard, SurfaceMessage } from "../../components/layout/PageLayout";
import { Button } from "../../components/ui/button";
import { Field, FieldLabel } from "../../components/ui/field";
import { Input } from "../../components/ui/input";
import { useCRMSetupBundle } from "../../domain/crm/hooks/useCRMSetupBundle";
import type { CRMPipelineReport, CRMPipelineReportParams, CRMPipelineSegment } from "../../domain/crm/types";
import { getCRMPipelineReport } from "../../lib/api/crm";
import { CRM_REPORTING_ROUTE, type AppRoute } from "../../lib/routes";

const SELECT_CLASS_NAME =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

const DEFAULT_FILTERS: CRMPipelineReportParams = {
  record_type: "all",
  scope: "open",
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

function SummaryCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-border/70 bg-background/50 p-4">
      <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-foreground">{value}</p>
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
  const { territoryOptions, customerGroupOptions, salesStageOptions } = useCRMSetupBundle();
  const [filters, setFilters] = useState<CRMPipelineReportParams>(DEFAULT_FILTERS);
  const [report, setReport] = useState<CRMPipelineReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  const groups = useMemo(() => {
    if (!report) {
      return {
        status: [] as CRMPipelineSegment[],
        salesStage: [] as CRMPipelineSegment[],
        territory: [] as CRMPipelineSegment[],
        customerGroup: [] as CRMPipelineSegment[],
        owner: [] as CRMPipelineSegment[],
        lostReason: [] as CRMPipelineSegment[],
        utmSource: [] as CRMPipelineSegment[],
        utmMedium: [] as CRMPipelineSegment[],
        utmCampaign: [] as CRMPipelineSegment[],
        utmContent: [] as CRMPipelineSegment[],
      };
    }

    return {
      status: report.by_status,
      salesStage: report.by_sales_stage,
      territory: report.by_territory,
      customerGroup: report.by_customer_group,
      owner: report.by_owner,
      lostReason: report.by_lost_reason,
      utmSource: report.by_utm_source,
      utmMedium: report.by_utm_medium ?? [],
      utmCampaign: report.by_utm_campaign ?? [],
      utmContent: report.by_utm_content ?? [],
    };
  }, [report]);

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: t("routes.crmReporting.label"), href: CRM_REPORTING_ROUTE as AppRoute }]}
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
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <SummaryCard label={t("crm.reporting.leadCount")} value={report.totals.lead_count} />
            <SummaryCard label={t("crm.reporting.opportunityCount")} value={report.totals.opportunity_count} />
            <SummaryCard label={t("crm.reporting.quotationCount")} value={report.totals.quotation_count} />
            <SummaryCard label={t("crm.reporting.openCount")} value={report.totals.open_count} />
            <SummaryCard label={t("crm.reporting.terminalCount")} value={report.totals.terminal_count} />
            <SummaryCard label={t("crm.reporting.openAmount")} value={report.totals.open_pipeline_amount} />
            <SummaryCard label={t("crm.reporting.terminalAmount")} value={report.totals.terminal_pipeline_amount} />
            <SummaryCard label={t("crm.reporting.orderedRevenue")} value={report.totals.ordered_revenue ?? "0.00"} />
          </div>

          <SectionCard title={t("crm.reporting.dropOffTitle")} description={t("crm.reporting.dropOffDescription")}>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <SummaryCard label={t("crm.reporting.dropOffLeadOnly")} value={report.dropoff.lead_only_count} />
              <SummaryCard label={t("crm.reporting.dropOffOpportunityWithoutQuotation")} value={report.dropoff.opportunity_without_quotation_count} />
              <SummaryCard label={t("crm.reporting.dropOffQuotationWithoutOrder")} value={report.dropoff.quotation_without_order_count} />
              <SummaryCard label={t("crm.reporting.dropOffQuotationWithOrder")} value={report.dropoff.quotation_with_order_count} />
            </div>
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
        </>
      ) : null}
    </div>
  );
}
