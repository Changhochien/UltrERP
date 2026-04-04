/** Reconciliation hooks for data fetching and mutations. */

import { useCallback, useState } from "react";
import type { ReconciliationResult, Payment } from "../types";
import { runReconciliation, confirmMatch, manualMatch } from "../../../lib/api/payments";

export function useRunReconciliation() {
	const [result, setResult] = useState<ReconciliationResult | null>(null);
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const execute = useCallback(async () => {
		setIsLoading(true);
		setError(null);
		try {
			const data = await runReconciliation();
			setResult(data);
			return data;
		} catch (e) {
			const msg = e instanceof Error ? e.message : "Unknown error";
			setError(msg);
			return null;
		} finally {
			setIsLoading(false);
		}
	}, []);

	return { result, isLoading, error, execute };
}

export function useConfirmMatch() {
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const execute = useCallback(async (paymentId: string): Promise<Payment | null> => {
		setIsLoading(true);
		setError(null);
		try {
			const result = await confirmMatch(paymentId);
			if (!result.ok) {
				setError(result.errors.map((e) => e.message).join("; "));
				return null;
			}
			return result.data;
		} catch (e) {
			const msg = e instanceof Error ? e.message : "Unknown error";
			setError(msg);
			return null;
		} finally {
			setIsLoading(false);
		}
	}, []);

	return { isLoading, error, execute };
}

export function useManualMatch() {
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const execute = useCallback(async (paymentId: string, invoiceId: string): Promise<Payment | null> => {
		setIsLoading(true);
		setError(null);
		try {
			const result = await manualMatch(paymentId, invoiceId);
			if (!result.ok) {
				setError(result.errors.map((e) => e.message).join("; "));
				return null;
			}
			return result.data;
		} catch (e) {
			const msg = e instanceof Error ? e.message : "Unknown error";
			setError(msg);
			return null;
		} finally {
			setIsLoading(false);
		}
	}, []);

	return { isLoading, error, execute };
}
