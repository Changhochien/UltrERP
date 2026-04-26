import { useCallback, useEffect, useState } from "react";

import { listCurrencies, type CurrencyRecord } from "../lib/api/currencies";
import {
  fetchPaymentTermsTemplates,
  type PaymentTermsTemplate,
} from "../lib/api/paymentTerms";

export interface CommercialDefaultsOptionsState {
  currencies: CurrencyRecord[];
  paymentTerms: PaymentTermsTemplate[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useCommercialDefaultsOptions(): CommercialDefaultsOptionsState {
  const [currencies, setCurrencies] = useState<CurrencyRecord[]>([]);
  const [paymentTerms, setPaymentTerms] = useState<PaymentTermsTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [currencyResponse, termsResponse] = await Promise.all([
        listCurrencies({ pageSize: 200, activeOnly: true }),
        fetchPaymentTermsTemplates(),
      ]);

      if (!termsResponse.ok) {
        throw new Error(termsResponse.error);
      }

      setCurrencies(currencyResponse.items.filter((currency) => currency.is_active));
      setPaymentTerms(termsResponse.data.items.filter((template) => template.is_active));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load commercial defaults");
      setCurrencies([]);
      setPaymentTerms([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { currencies, paymentTerms, loading, error, refresh };
}