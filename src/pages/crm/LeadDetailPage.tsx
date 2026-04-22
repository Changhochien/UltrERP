import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import type { CustomerCreatePayload } from "../../domain/customers/types";
import type {
  DuplicateLeadCandidate,
  LeadCreatePayload,
  LeadOpportunityHandoff,
  LeadResponse,
  LeadStatus,
} from "../../domain/crm/types";
import DuplicateLeadWarning from "../../components/crm/DuplicateLeadWarning";
import LeadForm from "../../components/crm/LeadForm";
import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Field, FieldLabel } from "../../components/ui/field";
import { Input } from "../../components/ui/input";
import { usePermissions } from "../../hooks/usePermissions";
import { useToast } from "../../hooks/useToast";
import {
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
  CRM_LEADS_ROUTE,
  CRM_OPPORTUNITY_CREATE_ROUTE,
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

export function LeadDetailPage({ onBack }: LeadDetailPageProps) {
  const { leadId } = useParams<{ leadId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation("common");
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
          converted_customer_id: result.data.customer_id,
        });
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
  const canAdvanceLead = canEditLead && lead.qualification_status === "qualified" && lead.status !== "converted";
  const createOpportunityPath = `${CRM_OPPORTUNITY_CREATE_ROUTE}?partyType=lead&partyName=${encodeURIComponent(lead.id)}&partyLabel=${encodeURIComponent(lead.company_name || lead.lead_name)}&territory=${encodeURIComponent(lead.territory)}&utmSource=${encodeURIComponent(lead.utm_source)}&utmMedium=${encodeURIComponent(lead.utm_medium)}&utmCampaign=${encodeURIComponent(lead.utm_campaign)}&utmContent=${encodeURIComponent(lead.utm_content)}`;

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[
          { label: t("routes.crmLeads.label"), href: CRM_LEADS_ROUTE },
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
            <Button type="button" onClick={handleOpportunityHandoff} disabled={!canAdvanceLead || handoffing}>
              {handoffing ? t("crm.detailPage.handoffing") : t("crm.detailPage.handoffAction")}
            </Button>
            <Button type="button" variant="outline" onClick={() => navigate(createOpportunityPath)} disabled={!canAdvanceLead}>
              {t("crm.detailPage.createOpportunity")}
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
          {lead.converted_customer_id ? (
            <Button type="button" variant="outline" onClick={() => navigate(buildCustomerDetailPath(lead.converted_customer_id!))}>
              {t("crm.detailPage.viewCustomer")}
            </Button>
          ) : null}
        </div>
      </SectionCard>
    </div>
  );
}

export default LeadDetailPage;
