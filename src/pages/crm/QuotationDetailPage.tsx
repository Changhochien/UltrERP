import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import QuotationForm from "../../components/crm/QuotationForm";
import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Field, FieldLabel } from "../../components/ui/field";
import { Input } from "../../components/ui/input";
import type { QuotationResponse, QuotationStatus } from "../../domain/crm/types";
import { usePermissions } from "../../hooks/usePermissions";
import { useToast } from "../../hooks/useToast";
import {
  getQuotation,
  QUOTATION_STATUS_OPTIONS,
  reviseQuotation,
  transitionQuotationStatus,
  updateQuotation,
} from "../../lib/api/crm";
import {
  toQuotationRevisionPayload,
  toQuotationTransitionPayload,
  toQuotationUpdatePayload,
  type QuotationFormValues,
} from "../../lib/schemas/quotation.schema";
import { buildQuotationDetailPath, CRM_QUOTATIONS_ROUTE } from "../../lib/routes";

const VERSION_CONFLICT_MESSAGE =
  "This quotation was changed elsewhere. The latest saved version has been reloaded.";

const SELECT_CLASS_NAME =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

const TRANSITIONABLE_STATUSES: QuotationStatus[] = QUOTATION_STATUS_OPTIONS.filter(
  (status) => !["partially_ordered", "ordered", "expired"].includes(status),
);

const STATUS_VARIANT: Record<QuotationStatus, "success" | "warning" | "outline"> = {
  draft: "outline",
  open: "outline",
  replied: "outline",
  partially_ordered: "outline",
  ordered: "success",
  lost: "warning",
  cancelled: "warning",
  expired: "warning",
};

interface QuotationDetailPageProps {
  onBack?: () => void;
}

export function QuotationDetailPage({ onBack }: QuotationDetailPageProps) {
  const { quotationId } = useParams<{ quotationId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation("common");
  const { canWrite } = usePermissions();
  const { error: showErrorToast, success: showSuccessToast } = useToast();
  const [quotation, setQuotation] = useState<QuotationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [serverErrors, setServerErrors] = useState<Array<{ field: string; message: string }>>([]);
  const [statusTarget, setStatusTarget] = useState<QuotationStatus>("open");
  const [transitioning, setTransitioning] = useState(false);
  const [lostReason, setLostReason] = useState("");
  const [competitorName, setCompetitorName] = useState("");
  const [lossNotes, setLossNotes] = useState("");
  const [revisionValidTill, setRevisionValidTill] = useState("");
  const [revisionNotes, setRevisionNotes] = useState("");
  const [revising, setRevising] = useState(false);

  useEffect(() => {
    if (!quotationId) {
      setError(t("crm.quotations.detailPage.notFound"));
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    getQuotation(quotationId)
      .then((data) => {
        if (cancelled) {
          return;
        }
        if (!data) {
          setQuotation(null);
          setError(t("crm.quotations.detailPage.notFound"));
          setLoading(false);
          return;
        }
        setQuotation(data);
        setStatusTarget(data.status === "draft" ? "open" : data.status);
        setLostReason(data.lost_reason);
        setCompetitorName(data.competitor_name);
        setLossNotes(data.loss_notes);
        setRevisionValidTill(data.valid_till ?? "");
        setRevisionNotes(data.notes ?? "");
        setLoading(false);
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setQuotation(null);
          setError(loadError instanceof Error ? loadError.message : t("crm.quotations.listPage.loadError"));
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [quotationId, t]);

  const availableStatusOptions = useMemo(
    () => TRANSITIONABLE_STATUSES.filter((status) => status !== quotation?.status),
    [quotation?.status],
  );

  const initialFormValues = useMemo<Partial<QuotationFormValues> | undefined>(() => {
    if (!quotation) {
      return undefined;
    }
    return {
      quotation_to: quotation.quotation_to,
      party_name: quotation.party_name,
      transaction_date: quotation.transaction_date,
      valid_till: quotation.valid_till,
      company: quotation.company,
      currency: quotation.currency,
      contact_person: quotation.contact_person,
      contact_email: quotation.contact_email,
      contact_mobile: quotation.contact_mobile,
      job_title: quotation.job_title,
      territory: quotation.territory,
      customer_group: quotation.customer_group,
      billing_address: quotation.billing_address,
      shipping_address: quotation.shipping_address,
      utm_source: quotation.utm_source,
      utm_medium: quotation.utm_medium,
      utm_campaign: quotation.utm_campaign,
      utm_content: quotation.utm_content,
      opportunity_id: quotation.opportunity_id ?? "",
      items: quotation.items.map((item) => ({
        item_name: item.item_name,
        item_code: item.item_code,
        description: item.description,
        quantity: item.quantity,
        unit_price: item.unit_price,
      })),
      taxes: quotation.taxes.map((tax) => ({
        description: tax.description,
        rate: tax.rate,
        tax_amount: tax.tax_amount,
      })),
      terms_template: quotation.terms_template,
      terms_and_conditions: quotation.terms_and_conditions,
      auto_repeat_enabled: quotation.auto_repeat_enabled,
      auto_repeat_frequency: quotation.auto_repeat_frequency,
      auto_repeat_until: quotation.auto_repeat_until ?? "",
      notes: quotation.notes,
    };
  }, [quotation]);

  useEffect(() => {
    if (availableStatusOptions.length > 0 && !availableStatusOptions.includes(statusTarget)) {
      setStatusTarget(availableStatusOptions[0]);
    }
  }, [availableStatusOptions, statusTarget]);

  async function handleSave(payload: ReturnType<typeof toQuotationUpdatePayload>) {
    if (!quotation) {
      return;
    }
    setServerErrors([]);
    setUpdating(true);
    try {
      const result = await updateQuotation(quotation.id, {
        ...payload,
        version: quotation.version,
      });
      if (result.ok) {
        setQuotation(result.data);
        showSuccessToast(
          t("crm.quotations.detailPage.toast.updateSuccessTitle"),
          t("crm.quotations.detailPage.toast.updateSuccessDescription", { name: result.data.party_label }),
        );
        return;
      }
      if (result.versionConflict) {
        const latest = await getQuotation(quotation.id).catch(() => null);
        if (latest) {
          setQuotation(latest);
        }
        setServerErrors([{ field: "", message: VERSION_CONFLICT_MESSAGE }]);
        showErrorToast(t("crm.quotations.detailPage.toast.updateErrorTitle"), VERSION_CONFLICT_MESSAGE);
        return;
      }
      setServerErrors(result.errors);
      showErrorToast(
        t("crm.quotations.detailPage.toast.updateErrorTitle"),
        result.errors[0]?.message ?? t("crm.quotations.detailPage.toast.updateErrorDescription"),
      );
    } finally {
      setUpdating(false);
    }
  }

  async function handleStatusTransition() {
    if (!quotation) {
      return;
    }
    setTransitioning(true);
    try {
      const result = await transitionQuotationStatus(
        quotation.id,
        toQuotationTransitionPayload({
          status: statusTarget,
          lost_reason: lostReason,
          competitor_name: competitorName,
          loss_notes: lossNotes,
        }),
      );
      if (result.ok) {
        setQuotation(result.data);
        setLostReason(result.data.lost_reason);
        setCompetitorName(result.data.competitor_name);
        setLossNotes(result.data.loss_notes);
        showSuccessToast(
          t("crm.quotations.detailPage.transitionSuccessTitle"),
          t("crm.quotations.detailPage.transitionSuccessDescription", {
            status: t(`crm.quotations.statusValues.${result.data.status}`),
          }),
        );
        return;
      }
      showErrorToast(
        t("crm.quotations.detailPage.transitionErrorTitle"),
        result.errors[0]?.message ?? t("crm.quotations.detailPage.transitionErrorDescription"),
      );
    } finally {
      setTransitioning(false);
    }
  }

  async function handleRevision() {
    if (!quotation) {
      return;
    }
    setRevising(true);
    try {
      const result = await reviseQuotation(
        quotation.id,
        toQuotationRevisionPayload({
          valid_till: revisionValidTill,
          notes: revisionNotes,
        }),
      );
      if (result.ok) {
        showSuccessToast(
          t("crm.quotations.detailPage.revisionSuccessTitle"),
          t("crm.quotations.detailPage.revisionSuccessDescription", { name: result.data.party_label }),
        );
        navigate(buildQuotationDetailPath(result.data.id));
        return;
      }
      showErrorToast(
        t("crm.quotations.detailPage.revisionErrorTitle"),
        result.errors[0]?.message ?? t("crm.quotations.detailPage.revisionErrorDescription"),
      );
    } finally {
      setRevising(false);
    }
  }

  if (loading) {
    return <p>{t("crm.quotations.detailPage.loading")}</p>;
  }

  if (error || !quotation) {
    return (
      <div className="space-y-6">
        <Button type="button" variant="outline" onClick={() => (onBack ? onBack() : navigate(CRM_QUOTATIONS_ROUTE))}>
          {t("crm.quotations.detailPage.backToList")}
        </Button>
        <div className="rounded-xl border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive" role="alert">
          {error ?? t("crm.quotations.detailPage.notFound")}
        </div>
      </div>
    );
  }

  const canEditQuotation = canWrite("crm");

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[
          { label: t("routes.crmQuotations.label"), href: CRM_QUOTATIONS_ROUTE },
          { label: quotation.party_label },
        ]}
        eyebrow={t("crm.quotations.detailPage.eyebrow")}
        title={quotation.party_label}
        description={`${quotation.company} · ${t(`crm.quotations.statusValues.${quotation.status}`)}`}
      />

      <SectionCard title={t("crm.quotations.detailPage.profileTitle")} description={t("crm.quotations.detailPage.profileDescription")}>
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={STATUS_VARIANT[quotation.status]} className="normal-case tracking-normal">
              {t(`crm.quotations.statusValues.${quotation.status}`)}
            </Badge>
            <Badge variant="outline" className="normal-case tracking-normal">
              {t(`crm.quotations.partyValues.${quotation.quotation_to}`)}
            </Badge>
            <Badge variant="outline" className="normal-case tracking-normal">
              {t("crm.quotations.detailPage.revisionBadge", { count: quotation.revision_no })}
            </Badge>
          </div>
          <div className="grid gap-3 rounded-xl border border-border/70 bg-muted/20 px-4 py-4 text-sm sm:grid-cols-3">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.quotations.form.subtotal")}</p>
              <p className="mt-1 font-medium">{quotation.subtotal}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.quotations.form.totalTaxes")}</p>
              <p className="mt-1 font-medium">{quotation.total_taxes}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("crm.quotations.form.grandTotal")}</p>
              <p className="mt-1 font-semibold">{quotation.grand_total}</p>
            </div>
          </div>
          <QuotationForm
            initialValues={initialFormValues}
            onSubmit={(payload) => handleSave(toQuotationUpdatePayload(payload, quotation.version))}
            serverErrors={serverErrors}
            submitLabel={t("crm.quotations.form.updateTitle")}
            submittingLabel={t("crm.quotations.form.updating")}
            submitting={updating}
            disabled={!canEditQuotation}
          />
        </div>
      </SectionCard>

      <SectionCard title={t("crm.quotations.detailPage.lifecycleTitle")} description={t("crm.quotations.detailPage.lifecycleDescription")}>
        <div className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
            <Field>
              <FieldLabel htmlFor="quotation-status-target">{t("crm.quotations.detailPage.transitionStatus")}</FieldLabel>
              <select
                id="quotation-status-target"
                className={SELECT_CLASS_NAME}
                value={statusTarget}
                onChange={(event) => setStatusTarget(event.target.value as QuotationStatus)}
                disabled={!canEditQuotation || availableStatusOptions.length === 0}
              >
                {availableStatusOptions.map((status) => (
                  <option key={status} value={status}>
                    {t(`crm.quotations.statusValues.${status}`)}
                  </option>
                ))}
              </select>
            </Field>
            <Button type="button" onClick={handleStatusTransition} disabled={!canEditQuotation || transitioning || availableStatusOptions.length === 0}>
              {transitioning ? t("crm.quotations.detailPage.transitioning") : t("crm.quotations.detailPage.transitionAction")}
            </Button>
          </div>

          {statusTarget === "lost" ? (
            <div className="grid gap-4 sm:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="lost_reason">{t("crm.quotations.detailPage.lostReason")}</FieldLabel>
                <Input id="lost_reason" value={lostReason} onChange={(event) => setLostReason(event.target.value)} />
              </Field>
              <Field>
                <FieldLabel htmlFor="competitor_name">{t("crm.quotations.detailPage.competitor")}</FieldLabel>
                <Input id="competitor_name" value={competitorName} onChange={(event) => setCompetitorName(event.target.value)} />
              </Field>
              <Field className="sm:col-span-2">
                <FieldLabel htmlFor="loss_notes">{t("crm.quotations.detailPage.lossNotes")}</FieldLabel>
                <Input id="loss_notes" value={lossNotes} onChange={(event) => setLossNotes(event.target.value)} />
              </Field>
            </div>
          ) : null}
        </div>
      </SectionCard>

      <SectionCard title={t("crm.quotations.detailPage.revisionTitle")} description={t("crm.quotations.detailPage.revisionDescription")}>
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] lg:items-end">
          <Field>
            <FieldLabel htmlFor="revision_valid_till">{t("crm.quotations.detailPage.revisionValidTill")}</FieldLabel>
            <Input id="revision_valid_till" type="date" value={revisionValidTill} onChange={(event) => setRevisionValidTill(event.target.value)} />
          </Field>
          <Field>
            <FieldLabel htmlFor="revision_notes">{t("crm.quotations.detailPage.revisionNotes")}</FieldLabel>
            <Input id="revision_notes" value={revisionNotes} onChange={(event) => setRevisionNotes(event.target.value)} />
          </Field>
          <Button type="button" onClick={handleRevision} disabled={!canEditQuotation || revising}>
            {revising ? t("crm.quotations.detailPage.revising") : t("crm.quotations.detailPage.revisionAction")}
          </Button>
        </div>
      </SectionCard>

      <SectionCard title={t("crm.quotations.detailPage.conversionTitle")} description={t("crm.quotations.detailPage.conversionDescription")}>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-muted-foreground">{t("crm.quotations.detailPage.conversionNote")}</p>
          <Button type="button" variant="outline" disabled>
            {t("crm.quotations.detailPage.conversionAction")}
          </Button>
        </div>
      </SectionCard>
    </div>
  );
}

export default QuotationDetailPage;