import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import OpportunityForm, { type OpportunityFormProps } from "@/domain/crm/components/OpportunityForm";
import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Field, FieldLabel } from "../../components/ui/field";
import { Input } from "../../components/ui/input";
import type { OpportunityQuotationHandoff, OpportunityResponse, OpportunityStatus } from "../../domain/crm/types";
import { usePermissions } from "../../hooks/usePermissions";
import { useToast } from "../../hooks/useToast";
import {
  getOpportunity,
  OPPORTUNITY_STATUS_OPTIONS,
  prepareOpportunityQuotationHandoff,
  transitionOpportunityStatus,
  updateOpportunity,
} from "../../lib/api/crm";
import {
  toOpportunityTransitionPayload,
  type OpportunityFormValues,
} from "../../lib/schemas/opportunity.schema";
import { CRM_OPPORTUNITIES_ROUTE, CRM_QUOTATION_CREATE_ROUTE } from "../../lib/routes";

const VERSION_CONFLICT_MESSAGE =
  "This opportunity was changed elsewhere. The latest saved version has been reloaded.";

const SELECT_CLASS_NAME =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

const STATUS_VARIANT: Record<OpportunityStatus, "success" | "warning" | "outline"> = {
  open: "outline",
  replied: "outline",
  quotation: "outline",
  converted: "success",
  closed: "warning",
  lost: "warning",
};

interface OpportunityDetailPageProps {
  onBack?: () => void;
}

export function OpportunityDetailPage({ onBack }: OpportunityDetailPageProps) {
  const { opportunityId } = useParams<{ opportunityId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation("crm");
const { t: tRoutes } = useTranslation("routes");
  const { canWrite } = usePermissions();
  const { error: showErrorToast, success: showSuccessToast } = useToast();
  const [opportunity, setOpportunity] = useState<OpportunityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [serverErrors, setServerErrors] = useState<Array<{ field: string; message: string }>>([]);
  const [statusTarget, setStatusTarget] = useState<OpportunityStatus>("replied");
  const [transitioning, setTransitioning] = useState(false);
  const [handoffing, setHandoffing] = useState(false);
  const [handoffPreview, setHandoffPreview] = useState<OpportunityQuotationHandoff | null>(null);
  const [lostReason, setLostReason] = useState("");
  const [competitorName, setCompetitorName] = useState("");
  const [lossNotes, setLossNotes] = useState("");

  useEffect(() => {
    if (!opportunityId) {
      setError(t("opportunities.detailPage.notFound"));
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    getOpportunity(opportunityId)
      .then((data) => {
        if (cancelled) {
          return;
        }
        if (!data) {
          setOpportunity(null);
          setError(t("opportunities.detailPage.notFound"));
          setLoading(false);
          return;
        }
        setOpportunity(data);
        setStatusTarget(data.status === "open" ? "replied" : data.status);
        setLostReason(data.lost_reason);
        setCompetitorName(data.competitor_name);
        setLossNotes(data.loss_notes);
        setLoading(false);
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setOpportunity(null);
          setError(loadError instanceof Error ? loadError.message : t("opportunities.listPage.loadError"));
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [opportunityId, t]);

  const availableStatusOptions = useMemo(
    () => OPPORTUNITY_STATUS_OPTIONS.filter((status) => status !== opportunity?.status),
    [opportunity?.status],
  );

  const initialFormValues = useMemo<Partial<OpportunityFormValues> | undefined>(() => {
    if (!opportunity) {
      return undefined;
    }
    return {
      opportunity_title: opportunity.opportunity_title,
      opportunity_from: opportunity.opportunity_from,
      party_name: opportunity.party_name,
      sales_stage: opportunity.sales_stage,
      probability: String(opportunity.probability),
      expected_closing: opportunity.expected_closing ?? "",
      currency: opportunity.currency,
      opportunity_amount: opportunity.opportunity_amount ?? "",
      opportunity_owner: opportunity.opportunity_owner,
      territory: opportunity.territory,
      customer_group: opportunity.customer_group,
      contact_person: opportunity.contact_person,
      contact_email: opportunity.contact_email,
      contact_mobile: opportunity.contact_mobile,
      job_title: opportunity.job_title,
      utm_source: opportunity.utm_source,
      utm_medium: opportunity.utm_medium,
      utm_campaign: opportunity.utm_campaign,
      utm_content: opportunity.utm_content,
      items: opportunity.items.map((item) => ({
        item_name: item.item_name,
        item_code: item.item_code,
        description: item.description,
        quantity: item.quantity,
        unit_price: item.unit_price,
      })),
      notes: opportunity.notes,
    };
  }, [opportunity]);

  useEffect(() => {
    if (availableStatusOptions.length > 0 && !availableStatusOptions.includes(statusTarget)) {
      setStatusTarget(availableStatusOptions[0]);
    }
  }, [availableStatusOptions, statusTarget]);

  async function handleSave(payload: Parameters<OpportunityFormProps["onSubmit"]>[0]) {
    if (!opportunity) {
      return;
    }
    setServerErrors([]);
    setUpdating(true);
    try {
      const result = await updateOpportunity(opportunity.id, {
        ...payload,
        version: opportunity.version,
      });
      if (result.ok) {
        setOpportunity(result.data);
        showSuccessToast(
          t("opportunities.detailPage.toast.updateSuccessTitle"),
          t("opportunities.detailPage.toast.updateSuccessDescription", { name: result.data.opportunity_title }),
        );
        return;
      }
      if (result.versionConflict) {
        const latest = await getOpportunity(opportunity.id).catch(() => null);
        if (latest) {
          setOpportunity(latest);
        }
        setServerErrors([{ field: "", message: VERSION_CONFLICT_MESSAGE }]);
        showErrorToast(t("opportunities.detailPage.toast.updateErrorTitle"), VERSION_CONFLICT_MESSAGE);
        return;
      }
      setServerErrors(result.errors);
      showErrorToast(
        t("opportunities.detailPage.toast.updateErrorTitle"),
        result.errors[0]?.message ?? t("opportunities.detailPage.toast.updateErrorDescription"),
      );
    } finally {
      setUpdating(false);
    }
  }

  async function handleStatusTransition() {
    if (!opportunity) {
      return;
    }
    setTransitioning(true);
    try {
      const result = await transitionOpportunityStatus(
        opportunity.id,
        toOpportunityTransitionPayload({
          status: statusTarget,
          lost_reason: lostReason,
          competitor_name: competitorName,
          loss_notes: lossNotes,
        }),
      );
      if (result.ok) {
        setOpportunity(result.data);
        setLostReason(result.data.lost_reason);
        setCompetitorName(result.data.competitor_name);
        setLossNotes(result.data.loss_notes);
        showSuccessToast(
          t("opportunities.detailPage.transitionSuccessTitle"),
          t("opportunities.detailPage.transitionSuccessDescription", {
            status: t(`opportunities.statusValues.${result.data.status}`),
          }),
        );
        return;
      }
      showErrorToast(
        t("opportunities.detailPage.transitionErrorTitle"),
        result.errors[0]?.message ?? t("opportunities.detailPage.transitionErrorDescription"),
      );
    } finally {
      setTransitioning(false);
    }
  }

  async function handleQuotationHandoff() {
    if (!opportunity) {
      return;
    }
    setHandoffing(true);
    try {
      const result = await prepareOpportunityQuotationHandoff(opportunity.id);
      if (result.ok) {
        setHandoffPreview(result.data);
        setOpportunity({ ...opportunity, status: "quotation" });
        showSuccessToast(
          t("opportunities.detailPage.handoffSuccessTitle"),
          t("opportunities.detailPage.handoffSuccessDescription", { name: result.data.opportunity_title }),
        );
        return;
      }
      showErrorToast(
        t("opportunities.detailPage.handoffErrorTitle"),
        result.errors[0]?.message ?? t("opportunities.detailPage.handoffErrorDescription"),
      );
    } finally {
      setHandoffing(false);
    }
  }

  if (loading) {
    return <p>{t("opportunities.detailPage.loading")}</p>;
  }

  if (error || !opportunity) {
    return (
      <div className="space-y-6">
        <Button type="button" variant="outline" onClick={() => (onBack ? onBack() : navigate(CRM_OPPORTUNITIES_ROUTE))}>
          {t("opportunities.detailPage.backToList")}
        </Button>
        <div className="rounded-xl border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive" role="alert">
          {error ?? t("opportunities.detailPage.notFound")}
        </div>
      </div>
    );
  }

  const canEditOpportunity = canWrite("crm");

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[
          { label: tRoutes("crmOpportunities.label"), href: CRM_OPPORTUNITIES_ROUTE },
          { label: opportunity.opportunity_title },
        ]}
        eyebrow={t("opportunities.detailPage.eyebrow")}
        title={opportunity.opportunity_title}
        description={`${opportunity.party_label} · ${t(`opportunities.statusValues.${opportunity.status}`)}`}
      />

      <SectionCard title={t("opportunities.detailPage.profileTitle")} description={t("opportunities.detailPage.profileDescription")}>
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={STATUS_VARIANT[opportunity.status]} className="normal-case tracking-normal">
              {t(`opportunities.statusValues.${opportunity.status}`)}
            </Badge>
            <Badge variant="outline" className="normal-case tracking-normal">
              {t(`crm.opportunities.partyValues.${opportunity.opportunity_from}`)}
            </Badge>
          </div>
          <OpportunityForm
            initialValues={initialFormValues}
            onSubmit={handleSave}
            serverErrors={serverErrors}
            submitLabel={t("opportunities.form.updateTitle")}
            submittingLabel={t("opportunities.form.updating")}
            submitting={updating}
            disabled={!canEditOpportunity}
          />
        </div>
      </SectionCard>

      <SectionCard title={t("opportunities.detailPage.lifecycleTitle")} description={t("opportunities.detailPage.lifecycleDescription")}>
        <div className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
            <Field>
              <FieldLabel htmlFor="opportunity-status-target">{t("opportunities.detailPage.transitionStatus")}</FieldLabel>
              <select
                id="opportunity-status-target"
                className={SELECT_CLASS_NAME}
                value={statusTarget}
                onChange={(event) => setStatusTarget(event.target.value as OpportunityStatus)}
                disabled={!canEditOpportunity || availableStatusOptions.length === 0}
              >
                {availableStatusOptions.map((status) => (
                  <option key={status} value={status}>
                    {t(`opportunities.statusValues.${status}`)}
                  </option>
                ))}
              </select>
            </Field>
            <Button type="button" onClick={handleStatusTransition} disabled={!canEditOpportunity || transitioning || availableStatusOptions.length === 0}>
              {transitioning ? t("opportunities.detailPage.transitioning") : t("opportunities.detailPage.transitionAction")}
            </Button>
          </div>

          {statusTarget === "lost" ? (
            <div className="grid gap-4 sm:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="lost_reason">{t("opportunities.detailPage.lostReason")}</FieldLabel>
                <Input id="lost_reason" value={lostReason} onChange={(event) => setLostReason(event.target.value)} />
              </Field>
              <Field>
                <FieldLabel htmlFor="competitor_name">{t("opportunities.detailPage.competitor")}</FieldLabel>
                <Input id="competitor_name" value={competitorName} onChange={(event) => setCompetitorName(event.target.value)} />
              </Field>
              <Field className="sm:col-span-2">
                <FieldLabel htmlFor="loss_notes">{t("opportunities.detailPage.lossNotes")}</FieldLabel>
                <Input id="loss_notes" value={lossNotes} onChange={(event) => setLossNotes(event.target.value)} />
              </Field>
            </div>
          ) : null}
        </div>
      </SectionCard>

      <SectionCard title={t("opportunities.detailPage.handoffTitle")} description={t("opportunities.detailPage.handoffDescription")}>
        <div className="space-y-4">
          <Button type="button" onClick={handleQuotationHandoff} disabled={!canEditOpportunity || handoffing}>
            {handoffing ? t("opportunities.detailPage.handoffing") : t("opportunities.detailPage.handoffAction")}
          </Button>
          {handoffPreview ? (
            <div className="rounded-xl border border-border/70 bg-muted/20 px-4 py-4 text-sm">
              <h3 className="font-semibold">{t("opportunities.detailPage.handoffPreviewTitle")}</h3>
              <p className="mt-1 text-muted-foreground">{t("opportunities.detailPage.handoffPreviewDescription")}</p>
              <dl className="mt-3 grid gap-3 sm:grid-cols-2">
                <div>
                  <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("opportunities.form.partyName")}</dt>
                  <dd className="mt-1">{handoffPreview.party_label}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("opportunities.form.currency")}</dt>
                  <dd className="mt-1">{handoffPreview.currency}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("opportunities.form.amount")}</dt>
                  <dd className="mt-1">{handoffPreview.opportunity_amount ?? "-"}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("opportunities.form.contactPerson")}</dt>
                  <dd className="mt-1">{handoffPreview.contact_person || "-"}</dd>
                </div>
              </dl>
              <div className="mt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate(CRM_QUOTATION_CREATE_ROUTE, { state: { handoff: handoffPreview } })}
                >
                  {t("opportunities.detailPage.createQuotation")}
                </Button>
              </div>
            </div>
          ) : null}
        </div>
      </SectionCard>
    </div>
  );
}

export default OpportunityDetailPage;