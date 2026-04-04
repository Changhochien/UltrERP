/** Payment hooks for data fetching and mutations. */

import { useCallback, useEffect, useState } from "react";
import type { PaymentCreate, PaymentListItem } from "../types";
import { createPayment, fetchPayments } from "../../../lib/api/payments";

export function usePayments(filters?: {
	invoice_id?: string;
	customer_id?: string;
	page?: number;
	page_size?: number;
}) {
	const [items, setItems] = useState<PaymentListItem[]>([]);
	const [total, setTotal] = useState(0);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const invoiceId = filters?.invoice_id;
	const customerId = filters?.customer_id;
	const page = filters?.page ?? 1;
	const pageSize = filters?.page_size ?? 20;

	const reload = useCallback(() => {
		setLoading(true);
		setError(null);
		fetchPayments({ invoice_id: invoiceId, customer_id: customerId, page, page_size: pageSize })
			.then((res) => {
				setItems(res.items);
				setTotal(res.total);
			})
			.catch((e) => setError(e.message))
			.finally(() => setLoading(false));
	}, [invoiceId, customerId, page, pageSize]);

	useEffect(() => {
		reload();
	}, [reload]);

	return { items, total, loading, error, reload };
}

export function useCreatePayment() {
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const mutate = useCallback(async (data: PaymentCreate) => {
		setIsLoading(true);
		setError(null);
		try {
			const result = await createPayment(data);
			if (!result.ok) {
				const msg = result.errors.map((e) => e.message).join("; ");
				setError(msg);
				return result;
			}
			return result;
		} finally {
			setIsLoading(false);
		}
	}, []);

	return { mutate, isLoading, error };
}
