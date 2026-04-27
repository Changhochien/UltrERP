/** Form to create a new sales order with dynamic line items. */

import { useEffect, useRef } from "react";
import { Controller, useFieldArray, useForm, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";

import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Button } from "../../../components/ui/button";
import { FieldError } from "../../../components/ui/field";
import { Input } from "../../../components/ui/input";
import { CustomerCombobox } from "@/domain/customers/components/CustomerCombobox";
import { ProductCombobox } from "@/domain/inventory/components/ProductCombobox";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../../components/ui/table";
import { usePaymentTerms, useCreateOrder } from "../hooks/useOrders";
import { trackEvent, AnalyticsEvents } from "../../../lib/analytics";
import {
  emptyOrderFormLine,
  emptyOrderSalesTeamMember,
  numericFieldOptions,
  orderFormSchema,
  toOrderCreatePayload,
  type OrderFormValues,
} from "../../../lib/schemas/order.schema";

interface OrderFormProps {
  initialCustomerId?: string;
  initialValues?: Partial<OrderFormValues>;
  conversionSource?: {
    quotationId: string;
    partyLabel: string;
  };
  onCreated: (orderId: string) => void;
  onCancel: () => void;
}

function snapshotText(snapshot: Record<string, unknown> | null | undefined, key: string): string {
  const value = snapshot?.[key];
  return typeof value === "string" ? value : "";
}

function buildDefaultValues(
  initialCustomerId?: string,
  initialValues?: Partial<OrderFormValues>,
): OrderFormValues {
  const crmContextSnapshot = initialValues?.crm_context_snapshot ?? null;
  return {
    customer_id: initialValues?.customer_id ?? initialCustomerId ?? "",
    source_quotation_id: initialValues?.source_quotation_id ?? "",
    payment_terms_code: initialValues?.payment_terms_code ?? "NET_30",
    discount_amount: initialValues?.discount_amount ?? 0,
    discount_percent: initialValues?.discount_percent ?? 0,
    utm_source: initialValues?.utm_source ?? snapshotText(crmContextSnapshot, "utm_source"),
    utm_medium: initialValues?.utm_medium ?? snapshotText(crmContextSnapshot, "utm_medium"),
    utm_campaign: initialValues?.utm_campaign ?? snapshotText(crmContextSnapshot, "utm_campaign"),
    utm_content: initialValues?.utm_content ?? snapshotText(crmContextSnapshot, "utm_content"),
    crm_context_snapshot: crmContextSnapshot,
    notes: initialValues?.notes ?? "",
    lines: initialValues?.lines?.length
      ? initialValues.lines.map((line) => ({ ...emptyOrderFormLine(), ...line }))
      : [emptyOrderFormLine()],
    sales_team: initialValues?.sales_team?.length ? initialValues.sales_team : [],
  };
}

export function OrderForm({
  initialCustomerId,
  initialValues,
  conversionSource,
  onCreated,
  onCancel,
}: OrderFormProps) {
  const { t } = useTranslation("orders");
  const { items: paymentTerms, loading: termsLoading, error: termsError } = usePaymentTerms();
  const { create, submitting, error, fieldErrors } = useCreateOrder();
  const submittingRef = useRef(false);
  const {
    control,
    handleSubmit,
    register,
    setError,
    setValue,
    watch,
    formState: { errors },
  } = useForm<OrderFormValues>({
    resolver: zodResolver(orderFormSchema as never) as Resolver<OrderFormValues>,
    defaultValues: buildDefaultValues(initialCustomerId, initialValues),
    mode: "onChange",
    reValidateMode: "onChange",
  });
  const {
    fields: lineFields,
    append: appendLine,
    remove: removeLine,
  } = useFieldArray({ control, name: "lines" });
  const {
    fields: salesTeamFields,
    append: appendSalesTeamMember,
    remove: removeSalesTeamMember,
  } = useFieldArray({ control, name: "sales_team" });

  useEffect(() => {
    if (!fieldErrors.length) {
      return;
    }

    for (const entry of fieldErrors) {
      if (!entry.field) {
        continue;
      }

      setError(entry.field as keyof OrderFormValues, { message: entry.message });
    }
  }, [fieldErrors, setError]);

  if (termsLoading) return <p aria-busy="true">{t("form.loading")}</p>;
  if (termsError) return <div role="alert" className="text-sm text-destructive">{termsError}</div>;

  const customerId = watch("customer_id");
  const lines = watch("lines");
  const salesTeam = watch("sales_team");
  const crmContextSnapshot = watch("crm_context_snapshot");
  const validLines = lines.filter(
    (line) => line.product_id && line.description.trim() && Number(line.quantity) > 0,
  );
  const validSalesTeam = salesTeam.filter(
    (member) => member.sales_person.trim() && Number(member.allocated_percentage) > 0,
  );
  const hasInvalidLines = lines.length > 0 && validLines.length < lines.length;
  const hasInvalidSalesTeam = salesTeam.length > 0 && validSalesTeam.length < salesTeam.length;
  const salesTeamAllocationTotal = validSalesTeam.reduce(
    (sum, member) => sum + Number(member.allocated_percentage || 0),
    0,
  );
  const hasAllocationOverflow = salesTeamAllocationTotal > 100;
  const commissionBasis = validLines.reduce(
    (sum, line) =>
      sum +
      (Number(line.quantity || 0) * Number(line.unit_price || 0)) - Number(line.discount_amount || 0),
    0,
  );
  const estimatedCommission = validSalesTeam.reduce(
    (sum, member) =>
      sum +
      (commissionBasis * Number(member.allocated_percentage || 0) * Number(member.commission_rate || 0)) /
        10000,
    0,
  );
  const canSubmit =
    Boolean(customerId) &&
    validLines.length > 0 &&
    !hasInvalidSalesTeam &&
    !hasAllocationOverflow;
  const attributionOrigin = typeof crmContextSnapshot?.["utm_attribution_origin"] === "string"
    ? crmContextSnapshot["utm_attribution_origin"]
    : null;

  const submitOrder = async (values: OrderFormValues) => {
    if (submittingRef.current) return;
    submittingRef.current = true;
    try {
      const result = await create(toOrderCreatePayload(values));
      if (result) {
        trackEvent(AnalyticsEvents.ORDER_CREATED, {
          source_page: conversionSource ? "/crm/quotations" : "/orders",
        });
        onCreated(result.id);
      }
    } finally {
      submittingRef.current = false;
    }
  };

  return (
    <section aria-label="Create order" className="space-y-5">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold tracking-tight">{t("form.newOrderTitle")}</h2>
        <p className="text-sm text-muted-foreground">{t("form.newOrderDescription")}</p>
      </div>

      {conversionSource ? (
        <SurfaceMessage>
          {t("form.preselectedQuotation", {
            quotationId: conversionSource.quotationId,
            partyLabel: conversionSource.partyLabel,
          })}{" "}
          {t("form.confirmationBoundary")}
        </SurfaceMessage>
      ) : initialCustomerId ? (
        <SurfaceMessage>{t("form.preselectedCustomer")}</SurfaceMessage>
      ) : null}

      {error ? <SurfaceMessage tone="danger">{error}</SurfaceMessage> : null}

      <form
        onSubmit={handleSubmit((values) => void submitOrder(values))}
        aria-label="Order form"
        className="space-y-6"
        noValidate
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <label className="space-y-2">
            <span>{t("form.customerId")}</span>
            <Controller
              name="customer_id"
              control={control}
              render={({ field }) => (
                <CustomerCombobox
                  value={field.value}
                  onChange={(value) => field.onChange(value)}
                  onClear={() => field.onChange("")}
                  placeholder={t("form.customerPlaceholder") ?? "Search customer by name or BAN…"}
                />
              )}
            />
            <FieldError>
              {errors.customer_id?.message ? t(errors.customer_id.message) : null}
            </FieldError>
          </label>

          <label className="space-y-2">
            <span>{t("form.paymentTerms")}</span>
            <select id="ord-terms" {...register("payment_terms_code")}>
              {paymentTerms.map((term) => (
                <option key={term.code} value={term.code}>
                  {term.label}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-2">
            <span>{t("form.notes")}</span>
            <Input id="ord-notes" type="text" {...register("notes")} placeholder="Optional notes" />
            <FieldError>
              {errors.notes?.message ? t(errors.notes.message) : null}
            </FieldError>
          </label>

          <label className="space-y-2">
            <span>{t("form.discountAmount")}</span>
            <Input
              id="ord-discount-amt"
              type="number"
              min={0}
              step="0.01"
              {...register("discount_amount", numericFieldOptions)}
              placeholder="0.00"
            />
            <FieldError>
              {errors.discount_amount?.message ? t(errors.discount_amount.message) : null}
            </FieldError>
          </label>

          <label className="space-y-2">
            <span>{t("form.discountPercent")} (%)</span>
            <Input
              id="ord-discount-pct"
              type="number"
              min={0}
              max={100}
              step="0.01"
              {...register("discount_percent", numericFieldOptions)}
              placeholder="0.00"
            />
            <FieldError>
              {errors.discount_percent?.message ? t(errors.discount_percent.message) : null}
            </FieldError>
          </label>
        </div>

        <SectionCard
          title={t("form.attributionTitle")}
          description={t("form.attributionDescription")}
        >
          <div className="space-y-4">
            {conversionSource ? (
              <SurfaceMessage>
                {attributionOrigin === "source_document"
                  ? t("form.attributionInherited")
                  : t("form.attributionOverrideHint")}
              </SurfaceMessage>
            ) : null}
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <label className="space-y-2">
                <span>{t("form.utmSource")}</span>
                <Input type="text" {...register("utm_source")} maxLength={120} />
                <FieldError>
                  {errors.utm_source?.message ? t(errors.utm_source.message) : null}
                </FieldError>
              </label>

              <label className="space-y-2">
                <span>{t("form.utmMedium")}</span>
                <Input type="text" {...register("utm_medium")} maxLength={120} />
                <FieldError>
                  {errors.utm_medium?.message ? t(errors.utm_medium.message) : null}
                </FieldError>
              </label>

              <label className="space-y-2">
                <span>{t("form.utmCampaign")}</span>
                <Input type="text" {...register("utm_campaign")} maxLength={120} />
                <FieldError>
                  {errors.utm_campaign?.message ? t(errors.utm_campaign.message) : null}
                </FieldError>
              </label>

              <label className="space-y-2">
                <span>{t("form.utmContent")}</span>
                <Input type="text" {...register("utm_content")} maxLength={200} />
                <FieldError>
                  {errors.utm_content?.message ? t(errors.utm_content.message) : null}
                </FieldError>
              </label>
            </div>
          </div>
        </SectionCard>

        <SectionCard
          title={t("form.commissionTitle")}
          description={t("form.commissionDescription")}
        >
          <div className="space-y-4">
            {salesTeamFields.length > 0 ? (
              <div className="grid gap-3">
                {salesTeamFields.map((member, idx) => (
                  <div
                    key={member.id}
                    className="grid gap-3 rounded-2xl border border-border/70 bg-background/50 p-4 md:grid-cols-[minmax(0,1.3fr)_minmax(0,0.8fr)_minmax(0,0.8fr)_auto]"
                  >
                    <label className="space-y-2">
                      <span>{t("form.salesPerson")}</span>
                      <Input
                        type="text"
                        {...register(`sales_team.${idx}.sales_person` as const)}
                        aria-label={`Commission rep ${idx + 1} salesperson`}
                        placeholder={t("form.salesPersonPlaceholder")}
                      />
                    </label>
                    <label className="space-y-2">
                      <span>{t("form.allocatedPercentage")}</span>
                      <Input
                        type="number"
                        min={0}
                        max={100}
                        step="0.01"
                        {...register(`sales_team.${idx}.allocated_percentage` as const, numericFieldOptions)}
                        aria-label={`Commission rep ${idx + 1} allocation percentage`}
                      />
                    </label>
                    <label className="space-y-2">
                      <span>{t("form.commissionRate")}</span>
                      <Input
                        type="number"
                        min={0}
                        max={100}
                        step="0.01"
                        {...register(`sales_team.${idx}.commission_rate` as const, numericFieldOptions)}
                        aria-label={`Commission rep ${idx + 1} commission rate`}
                      />
                    </label>
                    <div className="flex items-end">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeSalesTeamMember(idx)}
                        aria-label={`Remove commission rep ${idx + 1}`}
                      >
                        {t("delete")}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{t("form.commissionEmpty")}</p>
            )}

            <div className="grid gap-3 rounded-2xl border border-dashed border-border/70 bg-background/40 p-4 md:grid-cols-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                  {t("form.commissionBasis")}
                </p>
                <p className="mt-1 text-lg font-semibold text-foreground">${commissionBasis.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                  {t("form.allocatedTotal")}
                </p>
                <p className="mt-1 text-lg font-semibold text-foreground">{salesTeamAllocationTotal.toFixed(2)}%</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                  {t("form.estimatedCommission")}
                </p>
                <p className="mt-1 text-lg font-semibold text-foreground">${estimatedCommission.toFixed(2)}</p>
              </div>
            </div>

            <Button type="button" variant="outline" onClick={() => appendSalesTeamMember(emptyOrderSalesTeamMember())}>
              {t("form.addSalesPerson")}
            </Button>
          </div>
        </SectionCard>

        <div className="overflow-x-auto rounded-2xl border border-border/80 bg-card/90 shadow-sm">
          <Table aria-label="Order line items" className="min-w-[640px]">
            <TableHeader>
              <TableRow>
                <TableHead>{t("form.productId")}</TableHead>
                <TableHead>{t("form.description")}</TableHead>
                <TableHead>{t("form.quantity")}</TableHead>
                <TableHead>{t("form.unitPrice")}</TableHead>
                <TableHead>{t("form.discount")}</TableHead>
                <TableHead>{t("form.taxPolicy")}</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {lineFields.map((line, idx) => (
                <TableRow key={line.id}>
                  <TableCell>
                    <Controller
                      name={`lines.${idx}.product_id` as const}
                      control={control}
                      render={({ field }) => (
                        <ProductCombobox
                          value={field.value ?? ""}
                          onChange={(productId) => field.onChange(productId)}
                          onProductSelected={(product) => {
                            setValue(`lines.${idx}.description`, product.name, {
                              shouldDirty: true,
                              shouldValidate: true,
                            });
                          }}
                          placeholder="Search product…"
                        />
                      )}
                    />
                  </TableCell>
                  <TableCell>
                    <Input
                      type="text"
                      required
                      {...register(`lines.${idx}.description` as const)}
                      placeholder="Description"
                      aria-label={`Line ${idx + 1} description`}
                    />
                  </TableCell>
                  <TableCell>
                    <Input
                      type="number"
                      required
                      min={1}
                      step="any"
                      {...register(`lines.${idx}.quantity` as const, numericFieldOptions)}
                      aria-label={`Line ${idx + 1} quantity`}
                      className="w-24"
                    />
                  </TableCell>
                  <TableCell>
                    <Input
                      type="number"
                      required
                      min={0}
                      step="0.01"
                      {...register(`lines.${idx}.unit_price` as const, numericFieldOptions)}
                      aria-label={`Line ${idx + 1} unit price`}
                      className="w-28"
                    />
                  </TableCell>
                  <TableCell>
                    <Input
                      type="number"
                      min={0}
                      step="0.01"
                      {...register(`lines.${idx}.discount_amount` as const, numericFieldOptions)}
                      aria-label={`Line ${idx + 1} discount`}
                      className="w-24"
                    />
                  </TableCell>
                  <TableCell>
                    <select {...register(`lines.${idx}.tax_policy_code` as const)} aria-label={`Line ${idx + 1} tax policy`}>
                      <option value="standard">{t("form.taxPolicyStandard")}</option>
                      <option value="zero">{t("form.taxPolicyZero")}</option>
                      <option value="exempt">{t("form.taxPolicyExempt")}</option>
                      <option value="special">Special</option>
                    </select>
                  </TableCell>
                  <TableCell>
                    {lineFields.length > 1 ? (
                      <Button type="button" variant="ghost" size="sm" onClick={() => removeLine(idx)} aria-label={`Remove line ${idx + 1}`}>
                        {t("delete")}
                      </Button>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        <Button type="button" variant="outline" onClick={() => appendLine(emptyOrderFormLine())}>
          {t("form.addLine")}
        </Button>

        {hasInvalidLines ? (
          <SurfaceMessage tone="warning">
            {lines.length - validLines.length} line(s) incomplete — fill in product ID, description, and quantity (&gt; 0).
          </SurfaceMessage>
        ) : null}

        {hasInvalidSalesTeam ? (
          <SurfaceMessage tone="warning">
            {t("form.salesTeamIncomplete")}
          </SurfaceMessage>
        ) : null}

        {hasAllocationOverflow ? (
          <SurfaceMessage tone="danger">
            {t("form.salesTeamOverflow")}
          </SurfaceMessage>
        ) : null}

        {errors.sales_team?.message ? (
          <SurfaceMessage tone="danger">{t(errors.sales_team.message)}</SurfaceMessage>
        ) : null}

        <div className="flex gap-3">
          <Button type="submit" disabled={!canSubmit || submitting}>
            {submitting ? t("form.creating") : t("form.createOrder")}
          </Button>
          <Button type="button" variant="outline" onClick={onCancel}>
            {t("cancel")}
          </Button>
        </div>
      </form>
    </section>
  );
}
