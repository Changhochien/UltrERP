/** Modal dialog showing full customer details. */

import { useEffect, useState } from "react";

import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../ui/dialog";
import type { CustomerResponse } from "../../domain/customers/types";
import { getCustomer } from "../../lib/api/customers";

interface Props {
  customerId: string;
  onClose: () => void;
  onEdit?: () => void;
}

export function CustomerDetailDialog({ customerId, onClose, onEdit }: Props) {
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
          <DialogTitle>Customer Detail</DialogTitle>
          <DialogDescription>View the current billing and contact profile for this customer.</DialogDescription>
        </DialogHeader>
        {loading ? (
          <p>Loading…</p>
        ) : !customer ? (
          <p>Customer not found.</p>
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
              <dt>Company Name</dt>
              <dd>{customer.company_name}</dd>
              <dt>BAN</dt>
              <dd>{customer.normalized_business_number}</dd>
              <dt>Billing Address</dt>
              <dd>{customer.billing_address}</dd>
              <dt>Contact Name</dt>
              <dd>{customer.contact_name}</dd>
              <dt>Phone</dt>
              <dd>{customer.contact_phone}</dd>
              <dt>Email</dt>
              <dd>{customer.contact_email}</dd>
              <dt>Credit Limit</dt>
              <dd>{customer.credit_limit}</dd>
              <dt>Status</dt>
              <dd>{customer.status}</dd>
            </dl>
            {onEdit ? (
              <Button type="button" onClick={onEdit}>
                Edit
              </Button>
            ) : null}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
