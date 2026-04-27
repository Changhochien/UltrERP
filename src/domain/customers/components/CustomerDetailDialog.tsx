/** Modal dialog showing full customer details. */

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { CustomerResponse } from "@/domain/customers/types";
import { getCustomer } from "@/lib/api/customers";

interface Props {
  customerId: string;
  onClose: () => void;
  onEdit?: () => void;
}

export function CustomerDetailDialog({ customerId, onClose, onEdit }: Props) {
  const { t } = useTranslation("customer");
  const [customer, setCustomer] = useState<CustomerResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getCustomer(customerId)
      .then((c) => {
        if (!cancelled) {
          setCustomer(c);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCustomer(null);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [customerId]);

  return (
    <Dialog open onOpenChange={(open) => {
      if (!open) {
        onClose();
      }
    }}>
      <DialogContent className="w-[min(96vw,42rem)]">
        <DialogHeader>
          <DialogTitle>{t("detail.title")}</DialogTitle>
          <DialogDescription>{t("detail.description")}</DialogDescription>
        </DialogHeader>
        {loading ? (
          <p>{t("detail.loading")}</p>
        ) : !customer ? (
          <p>{t("detail.notFound")}</p>
        ) : (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={customer.status === "active" ? "success" : "outline"} className="normal-case tracking-normal">
                {customer.status}
              </Badge>
              <Badge variant="outline" className="normal-case tracking-normal">
                BAN {customer.normalized_business_number}
              </Badge>
            </div>
            <dl className="gap-y-4">
              <dt>{t("detail.companyName")}</dt>
              <dd>{customer.company_name}</dd>
              <dt>{t("detail.ban")}</dt>
              <dd>{customer.normalized_business_number}</dd>
              <dt>{t("detail.billingAddress")}</dt>
              <dd>{customer.billing_address}</dd>
              <dt>{t("detail.contactName")}</dt>
              <dd>{customer.contact_name}</dd>
              <dt>{t("detail.phone")}</dt>
              <dd>{customer.contact_phone}</dd>
              <dt>{t("detail.email")}</dt>
              <dd>{customer.contact_email}</dd>
              <dt>{t("detail.creditLimit")}</dt>
              <dd>{customer.credit_limit}</dd>
              <dt>{t("detail.status")}</dt>
              <dd>{customer.status}</dd>
            </dl>
            {onEdit ? (
              <Button type="button" onClick={onEdit}>
                {t("detail.edit")}
              </Button>
            ) : null}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
