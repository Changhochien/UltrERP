
import { useTranslation } from "react-i18next";

import type { InvoiceDraftLine } from "../../domain/invoices/types";
import { INVOICE_TAX_POLICY_OPTIONS } from "../../domain/invoices/types";

import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { ProductCombobox } from "../products/ProductCombobox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";

interface InvoiceLinePreview {
  subtotalAmount: number;
  taxAmount: number;
  totalAmount: number;
  taxType: number;
  taxRate: number;
}

interface InvoiceLineEditorProps {
  index: number;
  line: InvoiceDraftLine;
  preview: InvoiceLinePreview;
  currencyCode: string;
  canRemove: boolean;
  onChange: (next: InvoiceDraftLine) => void;
  onRemove: () => void;
}

function formatAmount(value: number): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function InvoiceLineEditor({
  index,
  line,
  preview,
  currencyCode,
  canRemove,
  onChange,
  onRemove,
}: InvoiceLineEditorProps) {
  const { t } = useTranslation("common");
  return (
    <fieldset className="space-y-4 rounded-2xl border border-border/80 bg-background/70 p-4 shadow-sm">
      <legend className="px-1 text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground">
        {t("invoice.lineEditor.lineNumber", { index: index + 1 })}
      </legend>
      <div className="grid gap-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1.5">
            <label htmlFor={`line-${index}-product-code`} className="text-sm font-medium">
              {t("invoice.lineEditor.productCode")}
            </label>
            <ProductCombobox
              value={line.product_id ?? ""}
              onChange={(productId) => onChange({ ...line, product_id: productId, product_code: line.product_code })}
              onProductSelected={(product) => onChange({ ...line, product_id: product.id, product_code: product.code, description: product.name })}
              placeholder="Search product…"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor={`line-${index}-description`} className="text-sm font-medium">
              {t("invoice.lineEditor.description")} *
            </label>
            <Input
              id={`line-${index}-description`}
              type="text"
              value={line.description}
              onChange={(event) => onChange({ ...line, description: event.target.value })}
              placeholder="Item description"
              required
            />
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="space-y-1.5">
            <label htmlFor={`line-${index}-quantity`} className="text-sm font-medium">
              {t("invoice.lineEditor.quantity")} *
            </label>
            <Input
              id={`line-${index}-quantity`}
              type="number"
              step="0.001"
              min="0.001"
              value={line.quantity}
              onChange={(event) => onChange({ ...line, quantity: event.target.value })}
              required
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor={`line-${index}-unit-price`} className="text-sm font-medium">
              {t("invoice.lineEditor.unitPrice")} *
            </label>
            <Input
              id={`line-${index}-unit-price`}
              type="number"
              step="0.01"
              min="0"
              value={line.unit_price}
              onChange={(event) => onChange({ ...line, unit_price: event.target.value })}
              required
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor={`line-${index}-tax-policy`} className="text-sm font-medium">
              {t("invoice.lineEditor.taxPolicy")} *
            </label>
            <Select
              value={line.tax_policy_code}
              onValueChange={(v) =>
                onChange({ ...line, tax_policy_code: v as InvoiceDraftLine["tax_policy_code"] })
              }
            >
              <SelectTrigger id={`line-${index}-tax-policy`}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {INVOICE_TAX_POLICY_OPTIONS.map((option) => (
                  <SelectItem key={option.code} value={option.code}>
                    {t(option.labelKey)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium">{t("invoice.lineEditor.lineTotal")}</label>
            <div className="flex h-10 items-center rounded-xl border border-input bg-muted/30 px-3 text-sm font-medium">
              {currencyCode} {formatAmount(preview.totalAmount)}
            </div>
          </div>
        </div>

        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <Badge variant="outline" className="justify-center normal-case tracking-normal">
            {t("invoice.lineEditor.taxType", { type: preview.taxType })}
          </Badge>
          <Badge variant="outline" className="justify-center normal-case tracking-normal">
            {t("invoice.lineEditor.rate", { rate: (preview.taxRate * 100).toFixed(0) })}
          </Badge>
          <Badge variant="outline" className="justify-center normal-case tracking-normal">
            {t("invoice.lineEditor.subtotal", { currency: currencyCode, amount: formatAmount(preview.subtotalAmount) })}
          </Badge>
          <Badge variant="outline" className="justify-center normal-case tracking-normal">
            {t("invoice.lineEditor.tax", { currency: currencyCode, amount: formatAmount(preview.taxAmount) })}
          </Badge>
        </div>

        {canRemove && (
          <div>
            <Button type="button" variant="outline" onClick={onRemove}>
              {t("invoice.lineEditor.removeLine")}
            </Button>
          </div>
        )}
      </div>
    </fieldset>
  );
}
