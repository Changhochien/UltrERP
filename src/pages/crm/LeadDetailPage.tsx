import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import type { CustomerCreatePayload } from "../../domain/customers/types";
import type {
  DuplicateLeadCandidate,
  LeadConversionPayload,
  LeadConversionStepResult,
  LeadCreatePayload,
  LeadOpportunityHandoff,
  LeadResponse,
  LeadStatus,
} from "../../domain/crm/types";
import DuplicateLeadWarning from "@/domain/crm/components/DuplicateLeadWarning";
import LeadForm from "@/domain/crm/components/LeadForm";
import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Field, FieldLabel } from "../../components/ui/field";
import { Input } from "../../components/ui/input";
import { usePermissions } from "../../hooks/usePermissions";
import { useToast } from "../../hooks/useToast";
import {
  convertLead,
  convertLeadToCustomer,
  getLead,
  handoffLeadToOpportunity,
  LEAD_STATUS_OPTIONS,
  transitionLeadStatus,
  updateLead,
} from "../../lib/api/crm";
import { toLeadUpdatePayload } from "../../lib/schemas/lead.schema";
import {
  buildCustomerDetailPath,
  buildLeadDetailPath,
  buildOpportunityDetailPath,
  buildQuotationDetailPath,
  CRM_LEADS_ROUTE,
  CRM_OPPORTUNITY_CREATE_ROUTE,
  CRM_QUOTATION_CREATE_ROUTE,
} from "../../lib/routes";

const VERSION_CONFLICT_MESSAGE =
  "This lead was changed elsewhere. The latest saved version has been reloaded.";

const MANUAL_STATUS_OPTIONS = LEAD_STATUS_OPTIONS.filter(
  (status) => status !== "opportunity" && status !== "converted",
) as Array<Exclude<LeadStatus, "opportunity" | "converted">>;

type ManualLeadStatus = Exclude<LeadStatus, "opportunity" | "converted">;

function normalizeManualStatusTarget(status: LeadStatus): ManualLeadStatus {
  if (status === "lead" || status === "opportunity" || status === "converted") {
    return "open";
  }

  return status;
}

const SELECT_CLASS_NAME =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

const STATUS_VARIANT: Record<LeadStatus, "success" | "warning" | "outline"> = {
  lead: "outline",
  open: "outline",
  replied: "outline",
  opportunity: "success",
  quotation: "outline",
  lost_quotation: "warning",
  interested: "success",
  converted: "success",
  do_not_contact: "warning",
};

interface LeadDetailPageProps {
  onBack?: () => void;
}

interface ConversionFormState {
  business_number: string;
  billing_address: string;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
}

interface ConversionPlanState {
  customer: boolean;
  opportunity: boolean;
  quotation: boolean;
}

function defaultConversionPlan(): ConversionPlanState {
  return {
    customer: false,
    opportunity: false,
    quotation: false,
  };
}

export function LeadDetailPage({ onBack }: LeadDetailPageProps) {
  const { leadId } = useParams<{ leadId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation("common");
const { t: tRoutes } = useTranslation("routes");
  const { canWrite } = usePermissions();
  const { error: showErrorToast, success: showSuccessToast } = useToast();
  const [lead, setLead] = useState<LeadResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [serverErrors, setServerErrors] = useState<Array<{ field: string; message: string }>>([]);
  const [updateDuplicate, setUpdateDuplicate] = useState<{ candidates: DuplicateLeadCandidate[] } | null>(null);
  const [statusTarget, setStatusTarget] = useState<ManualLeadStatus>("open");
  const [transitioning, setTransitioning] = useState(false);
  const [handoffing, setHandoffing] = useState(false);
  const [handoffPreview, setHandoffPreview] = useState<LeadOpportunityHandoff | null>(null);
  const [converting, setConverting] = useState(false);
  const [runningPlan, setRunningPlan] = useState(false);
  const [conversionPlan, setConversionPlan] = useState<ConversionPlanState>(defaultConversionPlan());
  const [conversionPlanSteps, setConversionPlanSteps] = useState<LeadConversionStepResult[]>([]);
  const [conversionForm, setConversionForm] = useState<ConversionFormState>({
    business_number: "",
    billing_address: "",
    contact_name: "",
    contact_phone: "",
    contact_email: "",
  });

  useEffect(() => {
    if (!leadId) {
      setError(t("crm.detailPage.notFound"));
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    getLead(leadId)
      .then((data) => {
        if (cancelled) {
          return;
        }
        if (!data) {
          setLead(null);
          setError(t("crm.detailPage.notFound"));
          setLoading(false);
          return;
        }
        setLead(data);
        setStatusTarget(normalizeManualStatusTarget(data.status));
        setConversionForm({
          business_number: "",
          billing_address: "",
          contact_name: data.lead_name,
          contact_phone: data.phone || data.mobile_no,
          contact_email: data.email_id,
        });
        setConversionPlan(defaultConversionPlan());
        setConversionPlanSteps([]);
        setLoading(false);
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setLead(null);
          setError(loadError instanceof Error ? loadError.message : t("crm.listPage.loadError"));
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [leadId, t]);

  const availableStatusOptions = useMemo(
    () => MANUAL_STATUS_OPTIONS.filter((status) => status !== lead?.status),
    [lead?.status],
  );

  const initialFormValues = useMemo(
    () =>
      lead
        ? {
            lead_name: lead.lead_name,
            company_name: lead.company_name,
            email_id: lead.email_id,
            phone: lead.phone,
            mobile_no: lead.mobile_no,
            territory: lead.territory,
            lead_owner: lead.lead_owner,
            source: lead.source,
            qualification_status: lead.qualification_status,
            qualified_by: lead.qualified_by,
            annual_revenue: lead.annual_revenue ?? "",
            no_of_employees: lead.no_of_employees != null ? String(lead.no_of_employees) : "",
            industry: lead.industry,
            market_segment: lead.market_segment,
            utm_source: lead.utm_source,
            utm_medium: lead.utm_medium,
            utm_campaign: lead.utm_campaign,
            utm_content: lead.utm_content,
            notes: lead.notes,
          }
        : undefined,
    [lead],
  );

  useEffect(() => {
    if (availableStatusOptions.length > 0 && !availableStatusOptions.includes(statusTarget)) {
      setStatusTarget(availableStatusOptions[0]);
    }
  }, [availableStatusOptions, statusTarget]);

  function handleOpenDuplicateCandidate(candidate: DuplicateLeadCandidate) {
    if (candidate.kind === "lead") {
      navigate(buildLeadDetailPath(candidate.id));
      return;
    }
    navigate(buildCustomerDetailPath(candidate.id));
  }

  async function handleSave(payload: LeadCreatePayload) {
    if (!lead) {
      return;
    }
    setServerErrors([]);
    setUpdateDuplicate(null);
    setUpdating(true);
    try {
      const result = await updateLead(lead.id, toLeadUpdatePayload(payload, lead.version));
      if (result.ok) {
        setLead(result.data);
        showSuccessToast(
          t("crm.detailPage.toast.updateSuccessTitle"),
          t("crm.detailPage.toast.updateSuccessDescription", { name: result.data.lead_name }),
        );
        return;
      }

      if (result.duplicate) {
        setUpdateDuplicate(result.duplicate);
        return;
      }

      if (result.versionConflict) {
        const latest = await getLead(lead.id).catch(() => null);
        if (latest) {
          setLead(latest);
        }
        setServerErrors([{ field: "", message: VERSION_CONFLICT_MESSAGE }]);
        showErrorToast(t("crm.detailPage.toast.updateErrorTitle"), VERSION_CONFLICT_MESSAGE);
        return;
      }

      setServerErrors(result.errors);
      showErrorToast(
        t("crm.detailPage.toast.updateErrorTitle"),
        result.errors[0]?.message ?? t("crm.detailPage.toast.updateErrorDescription"),
      );
    } finally {
      setUpdating(false);
    }
  }

  async function handleStatusTransition() {
    if (!lead) {
      return;
    }
    setTransitioning(true);
    try {
      const result = await transitionLeadStatus(lead.id, statusTarget);
      if (result.ok) {
        setLead(result.data);
        showSuccessToast(
          t("crm.detailPage.transitionSuccessTitle"),
          t("crm.detailPage.transitionSuccessDescription", {
            status: t(`crm.statusValues.${result.data.status}`),
          }),
        );
        return;
      }
      showErrorToast(
        t("crm.detailPage.transitionErrorTitle"),
        result.errors[0]?.message ?? t("crm.detailPage.transitionErrorDescription"),
      );
    } finally {
      setTransitioning(false);
    }
  }

  async function handleOpportunityHandoff() {
    if (!lead) {
      return;
    }
    setHandoffing(true);
    try {
      const result = await handoffLeadToOpportunity(lead.id);
      if (result.ok) {
        setHandoffPreview(result.data);
        setLead({ ...lead, status: "opportunity" });
        showSuccessToast(
          t("crm.detailPage.handoffSuccessTitle"),
          t("crm.detailPage.handoffSuccessDescription", { name: result.data.lead_name }),
        );
        return;
      }
      showErrorToast(
        t("crm.detailPage.handoffErrorTitle"),
        result.errors[0]?.message ?? t("crm.detailPage.handoffErrorDescription"),
      );
    } finally {
      setHandoffing(false);
    }
  }

  async function handleConvertToCustomer() {
    if (!lead) {
      return;
    }

    const customerPayload: CustomerCreatePayload = {
      company_name: lead.company_name || lead.lead_name,
      business_number: conversionForm.business_number.trim(),
      billing_address: conversionForm.billing_address.trim(),
      contact_name: conversionForm.contact_name.trim(),
      contact_phone: conversionForm.contact_phone.trim(),
      contact_email: conversionForm.contact_email.trim().toLowerCase(),
      credit_limit: "0.00",
    };

    setConverting(true);
    try {
      const result = await convertLeadToCustomer(lead.id, customerPayload);
      if (result.ok) {
        setLead({
          ...lead,
          status: result.data.status,
          conversion_state: "converted",
          conversion_path: "customer",
          converted_customer_id: result.data.customer_id,
          converted_at: new Date().toISOString(),
        });
        setConversionPlanSteps([
          {
            target: "customer",
            outcome: "created",
            record_id: result.data.customer_id,
            errors: [],
          },
        ]);
        showSuccessToast(
          t("crm.detailPage.convertSuccessTitle"),
          t("crm.detailPage.convertSuccessDescription", { customerId: result.data.customer_id }),
        );
        return;
      }
      showErrorToast(
        t("crm.detailPage.convertErrorTitle"),
        result.errors[0]?.message ?? t("crm.detailPage.convertErrorDescription"),
      );
    } finally {
      setConverting(false);
    }
  }

  function handleTogglePlanTarget(target: keyof ConversionPlanState) {
    setConversionPlan((current) => ({
      ...current,
      [target]: !current[target],
    }));
  }

  function buildOpportunityConversionPayload(): LeadConversionPayload["opportunity"] {
    if (!lead) {
      return undefined;
    }
    return {
      opportunity_title: `${lead.company_name || lead.lead_name} Opportunity`,
      opportunity_from: "lead",
      party_name: lead.id,
      sales_stage: "qualification",
      probability: 0,
      expected_closing: null,
      currency: "TWD",
      opportunity_amount: null,
      opportunity_owner: lead.lead_owner,
      territory: lead.territory,
      customer_group: "",
      contact_person: lead.lead_name,
      contact_email: lead.email_id,
      contact_mobile: lead.phone || lead.mobile_no,
      job_title: "",
      utm_source: lead.utm_source,
      utm_medium: lead.utm_medium,
      utm_campaign: lead.utm_campaign,
      utm_content: lead.utm_content,
      items: [],
      notes: lead.notes,
    };
  }

  async function handleRunConversionPlan() {
    if (!lead) {
      return;
    }

    const hasImmediateTargets = conversionPlan.customer || conversionPlan.opportunity;
    if (!hasImmediateTargets && !conversionPlan.quotation) {
      showErrorToast(
        t("crm.detailPage.planErrorTitle"),
        t("crm.detailPage.planSelectTargetError"),
      );
      return;
    }

    if (!hasImmediateTargets && conversionPlan.quotation) {
      navigate(createQuotationPath);
      return;
    }

    const payload: LeadConversionPayload = {};
    if (conversionPlan.customer) {
      payload.customer = {
        company_name: lead.company_name || lead.lead_name,
        business_number: conversionForm.business_number.trim(),
        billing_address: conversionForm.billing_address.trim(),
        contact_name: conversionForm.contact_name.trim(),
        contact_phone: conversionForm.contact_phone.trim(),
        contact_email: conversionForm.contact_email.trim().toLowerCase(),
        credit_limit: "0.00",
      };
    }
    if (conversionPlan.opportunity) {
      payload.opportunity = buildOpportunityConversionPayload();
    }

    setRunningPlan(true);
    setConversionPlanSteps([]);
    try {
      const result = await convertLead(lead.id, payload);
      if (!result.ok) {
        showErrorToast(
          t("crm.detailPage.planErrorTitle"),
          result.errors[0]?.message ?? t("crm.detailPage.planErrorDescription"),
        );
        return;
      }

      setLead({
        ...lead,
        status: result.data.status,
        conversion_state: result.data.conversion_state,
        conversion_path: result.data.conversion_path,
        converted_by: result.data.converted_by,
        converted_customer_id: result.data.converted_customer_id,
        converted_opportunity_id: result.data.converted_opportunity_id,
        converted_quotation_id: result.data.converted_quotation_id,
        converted_at: result.data.converted_at,
      });
      setConversionPlanSteps(result.data.steps);

      const failedStep = result.data.steps.find((step) => step.outcome === "failed");
      if (failedStep) {
        showErrorToast(
          t("crm.detailPage.planPartialTitle"),
          failedStep.errors[0]?.message ?? t("crm.detailPage.planPartialDescription"),
        );
        return;
      }

      showSuccessToast(
        t("crm.detailPage.planSuccessTitle"),
        t("crm.detailPage.planSuccessDescription"),
      );
      if (conversionPlan.quotation) {
        navigate(createQuotationPath);
      }
    } finally {
      setRunningPlan(false);
    }
  }

  if (loading) {
    return <p>{t("crm.detailPage.loading")}</p>;
  }

  if (error || !lead) {
    return (
      <div className="space-y-6">
        <Button type="button" variant="outline" onClick={() => (onBack ? onBack() : navigate(CRM_LEADS_ROUTE))}>
          {t("crm.detailPage.backToList")}
        </Button>
        <div className="rounded-xl border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive" role="alert">
          {error ?? t("crm.detailPage.notFound")}
        </div>
      </div>
    );
  }

  const canEditLead = canWrite("crm");
  const canAdvanceLead = canEditLead && lead.qualification_status === "qualified" && lead.status !== "do_not_contact";
  const canUseOpportunityHandoff = canAdvanceLead && lead.status !== "converted";
  const createOpportunityPath = `${CRM_OPPORTUNITY_CREATE_ROUTE}?partyType=lead&partyName=${encodeURIComponent(lead.id)}&partyLabel=${encodeURIComponent(lead.company_name || lead.lead_name)}&territory=${encodeURIComponent(lead.territory)}&utmSource=${encodeURIComponent(lead.utm_source)}&utmMedium=${encodeURIComponent(lead.utm_medium)}&utmCampaign=${encodeURIComponent(lead.utm_campaign)}&utmContent=${encodeURIComponent(lead.utm_content)}`;
  const createQuotationPath = `${CRM_QUOTATION_CREATE_ROUTE}?partyType=lead&partyName=${encodeURIComponent(lead.id)}&partyLabel=${encodeURIComponent(lead.company_name || lead.lead_name)}&territory=${encodeURIComponent(lead.territory)}&contactName=${encodeURIComponent(lead.lead_name)}&contactEmail=${encodeURIComponent(lead.email_id)}&contactMobile=${encodeURIComponent(lead.phone || lead.mobile_no)}&utmSource=${encodeURIComponent(lead.utm_source)}&utmMedium=${encodeURIComponent(lead.utm_medium)}&utmCampaign=${encodeURIComponent(lead.utm_campaign)}&utmContent=${encodeURIComponent(lead.utm_content)}`;
  const conversionPathLabel = lead.conversion_path
    ? lead.conversion_path
        .split("+")
        .map((target) => t(`crm.detailPage.conversionTarget.${target}`))
        .join(" + ")
    : "-";

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[
          { label: tRoutes("crmLeads.label"), href: CRM_LEADS_ROUTE },
          { label: lead.company_name || lead.lead_name },
        ]}
        eyebrow={t("crm.detailPage.eyebrow")}
        title={lead.company_name || lead.lead_name}
        description={`${t(`crm.statusValues.${lead.status}`)} · ${t(`crm.qualificationValues.${lead.qualification_status}`)}`}
      />

      <SectionCard title={t("crm.detailPage.profileTitle")} description={t("crm.detailPage.profileDescription")}>
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={STATUS_VARIANT[lead.status]} className="normal-case tracking-normal">
              {t(`crm.statusValues.${lead.status}`)}
            </Badge>
            <Badge variant="outline" className="normal-case tracking-normal">
              {t(`crm.qualificationValues.${lead.qualification_status}`)}
            </Badge>
          </div>
          {updateDuplicate ? (
            <DuplicateLeadWarning
              duplicate={updateDuplicate}
              onOpenCandidate={handleOpenDuplicateCandidate}
              onCancel={() => setUpdateDuplicate(null)}
            />
          ) : null}
          <LeadForm
            initialValues={initialFormValues}
            onSubmit={handleSave}
            serverErrors={serverErrors}
            submitLabel={t("crm.form.updateTitle")}
            submittingLabel={t("crm.form.updating")}
            submitting={updating}
            disabled={!canEditLead}
          />
        </div>
      </SectionCard>

      <SectionCard title={t("crm.detailPage.lifecycleTitle")} description={t("crm.detailPage.lifecycleDescription")}>
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
          <Field>
            <FieldLabel htmlFor="lead-status-target">{t("crm.detailPage.transitionStatus")}</FieldLabel>
            <select
              id="lead-status-target"
              className={SELECT_CLASS_NAME}
              value={statusTarget}
              onChange={(event) => setStatusTarget(event.target.value as ManualLeadStatus)}
              disabled={!canEditLead || availableStatusOptions.length === 0}
            >
              {availableStatusOptions.map((status) => (
                <option key={status} value={status}>
                  {t(`crm.statusValues.${status}`)}
                </option>
              ))}
            </select>
          </Field>
          <Button type="button" onClick={handleStatusTransition} disabled={!canEditLead || transitioning || availableStatusOptions.length === 0}>
            {transitioning ? t("crm.detailPage.transitioning") : t("crm.detailPage.transitionAction")}
          </Button>
        </div>
      </SectionCard>

      <SectionCard title={t("crm.detailPage.handoffTitle")} description={t("crm.detailPage.handoffDescription")}>
        <div className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <Button type="button" onClick={handleOpportunityHandoff} disabled={!canUseOpportunityHandoff || handoffing}>
              {handoffing ? t("crm.detailPage.handoffing") : t("crm.detailPage.handoffAction")}
            </Button>
            <Button type="button" variant="outline" onClick={() => navigate(createOpportunityPath)} disabled={!canAdvanceLead}>
              {t("crm.detailPage.createOpportunity")}
            </Button>
            <Button type="button" variant="outline" onClick={() => navigate(createQuotationPath)} disabled={!canAdvanceLead}>
              {t("crm.detailPage.createQuotation")}
            </Button>
          </div>
          {handoffPreview ? (
            <div className="rounded-xl border border-border/70 bg-muted/20 px-4 py-4 text-sm">
              <h3 className="font-semibold">{t("crm.detailPage.handoffPreviewTitle")}</h3>
              <p className="mt-1 text-muted-foreground">{t("crm.detailPage.handoffPreviewDescription")}</p>
              <dl className="mt-3 grid gap-3 sm:grid-cols-2">
                <div>
                  <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.form.owner")}</dt>
                  <dd className="mt-1">{handoffPreview.lead_owner || "-"}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.form.territory")}</dt>
                  <dd className="mt-1">{handoffPreview.territory || "-"}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.form.utmCampaign")}</dt>
                  <dd className="mt-1">{handoffPreview.utm_campaign || "-"}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.form.source")}</dt>
                  <dd className="mt-1">{handoffPreview.source || "-"}</dd>
                </div>
              </dl>
            </div>
          ) : null}
        </div>
      </SectionCard>

      <SectionCard title={t("crm.detailPage.convertTitle")} description={t("crm.detailPage.convertDescription")}>
        <div className="mb-5 rounded-xl border border-border/70 bg-background/40 p-4">
          <h3 className="font-semibold text-foreground">{t("crm.detailPage.planTitle")}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{t("crm.detailPage.planDescription")}</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {(["customer", "opportunity", "quotation"] as Array<keyof ConversionPlanState>).map((target) => (
              <label key={target} className="flex items-start gap-3 rounded-xl border border-border/70 bg-background/50 px-3 py-3 text-sm">
                <input
                  type="checkbox"
                  checked={conversionPlan[target]}
                  onChange={() => handleTogglePlanTarget(target)}
                  disabled={!canAdvanceLead || runningPlan}
                />
                <span>
                  <span className="font-medium text-foreground">{t(`crm.detailPage.conversionTarget.${target}`)}</span>
                  <span className="block text-muted-foreground">{t(`crm.detailPage.planTargetDescription.${target}`)}</span>
                </span>
              </label>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <Button type="button" variant="outline" onClick={handleRunConversionPlan} disabled={!canAdvanceLead || runningPlan}>
              {runningPlan ? t("crm.detailPage.planRunning") : t("crm.detailPage.planAction")}
            </Button>
          </div>
          {conversionPlanSteps.length ? (
            <div className="mt-4 space-y-3 rounded-xl border border-border/70 bg-muted/20 p-4 text-sm">
              <h4 className="font-semibold text-foreground">{t("crm.detailPage.planResultsTitle")}</h4>
              {conversionPlanSteps.map((step) => (
                <div key={`${step.target}-${step.record_id ?? step.outcome}`} className="rounded-lg border border-border/60 bg-background/50 px-3 py-3">
                  <p className="font-medium text-foreground">
                    {t(`crm.detailPage.conversionTarget.${step.target}`)} · {t(`crm.detailPage.planOutcome.${step.outcome}`)}
                  </p>
                  {step.record_id ? <p className="mt-1 text-muted-foreground">{step.record_id}</p> : null}
                  {step.errors.map((entry) => (
                    <p key={`${step.target}-${entry.field}-${entry.message}`} className="mt-1 text-destructive">
                      {entry.message}
                    </p>
                  ))}
                </div>
              ))}
            </div>
          ) : null}
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <Field>
            <FieldLabel htmlFor="convert-business-number">{t("crm.detailPage.convertBusinessNumber")}</FieldLabel>
            <Input
              id="convert-business-number"
              value={conversionForm.business_number}
              onChange={(event) => setConversionForm((current) => ({ ...current, business_number: event.target.value }))}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="convert-contact-name">{t("crm.detailPage.convertContactName")}</FieldLabel>
            <Input
              id="convert-contact-name"
              value={conversionForm.contact_name}
              onChange={(event) => setConversionForm((current) => ({ ...current, contact_name: event.target.value }))}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="convert-contact-phone">{t("crm.detailPage.convertContactPhone")}</FieldLabel>
            <Input
              id="convert-contact-phone"
              value={conversionForm.contact_phone}
              onChange={(event) => setConversionForm((current) => ({ ...current, contact_phone: event.target.value }))}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="convert-contact-email">{t("crm.detailPage.convertContactEmail")}</FieldLabel>
            <Input
              id="convert-contact-email"
              value={conversionForm.contact_email}
              onChange={(event) => setConversionForm((current) => ({ ...current, contact_email: event.target.value }))}
            />
          </Field>
          <Field className="sm:col-span-2">
            <FieldLabel htmlFor="convert-billing-address">{t("crm.detailPage.convertBillingAddress")}</FieldLabel>
            <Input
              id="convert-billing-address"
              value={conversionForm.billing_address}
              onChange={(event) => setConversionForm((current) => ({ ...current, billing_address: event.target.value }))}
            />
          </Field>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button type="button" onClick={handleConvertToCustomer} disabled={!canAdvanceLead || converting}>
            {converting ? t("crm.detailPage.converting") : t("crm.detailPage.convertAction")}
          </Button>
        </div>
        {(lead.converted_customer_id || lead.converted_opportunity_id || lead.converted_quotation_id || lead.converted_at) ? (
          <div className="mt-4 rounded-xl border border-border/70 bg-muted/20 px-4 py-4 text-sm">
            <h3 className="font-semibold">{t("crm.detailPage.conversionSummaryTitle")}</h3>
            <p className="mt-1 text-muted-foreground">{t("crm.detailPage.conversionSummaryDescription")}</p>
            <dl className="mt-3 grid gap-3 sm:grid-cols-2">
              <div>
                <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.detailPage.conversionState")}</dt>
                <dd className="mt-1">{t(`crm.conversionStateValues.${lead.conversion_state}`)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.detailPage.conversionPath")}</dt>
                <dd className="mt-1">{conversionPathLabel}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.detailPage.convertedAt")}</dt>
                <dd className="mt-1">{lead.converted_at ? new Date(lead.converted_at).toLocaleString() : "-"}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.detailPage.convertedBy")}</dt>
                <dd className="mt-1">{lead.converted_by || "-"}</dd>
              </div>
            </dl>
            <div className="mt-4 flex flex-wrap gap-3">
              {lead.converted_customer_id ? (
                <Button type="button" variant="outline" onClick={() => navigate(buildCustomerDetailPath(lead.converted_customer_id!))}>
                  {t("crm.detailPage.viewCustomer")}
                </Button>
              ) : null}
              {lead.converted_opportunity_id ? (
                <Button type="button" variant="outline" onClick={() => navigate(buildOpportunityDetailPath(lead.converted_opportunity_id!))}>
                  {t("crm.detailPage.viewOpportunity")}
                </Button>
              ) : null}
              {lead.converted_quotation_id ? (
                <Button type="button" variant="outline" onClick={() => navigate(buildQuotationDetailPath(lead.converted_quotation_id!))}>
                  {t("crm.detailPage.viewQuotation")}
                </Button>
              ) : null}
            </div>
          </div>
        ) : null}
      </SectionCard>
    </div>
  );
}

export default LeadDetailPage;
