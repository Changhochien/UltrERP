import { useCallback, useEffect, useState } from "react";

import { fetchSupplier, fetchSuppliers } from "../../../lib/api/inventory";
import type { Supplier, SupplierListOptions } from "../types";

interface UseSuppliersOptions extends SupplierListOptions {
  autoLoad?: boolean;
}

export function useSuppliers(options?: UseSuppliersOptions) {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(options?.autoLoad === false ? false : true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    const response = await fetchSuppliers({
      q: options?.q,
      activeOnly: options?.activeOnly,
      limit: options?.limit,
      offset: options?.offset,
    });

    if (response.ok) {
      setSuppliers(response.data.items);
      setTotal(response.data.total);
    } else {
      setSuppliers([]);
      setTotal(0);
      setError(response.error);
    }
    setLoading(false);
  }, [options?.activeOnly, options?.limit, options?.offset, options?.q]);

  useEffect(() => {
    if (options?.autoLoad === false) {
      return;
    }
    void reload();
  }, [options?.autoLoad, reload]);

  return { suppliers, total, loading, error, reload };
}

export function useSupplierDetail(supplierId: string | null) {
  const [supplier, setSupplier] = useState<Supplier | null>(null);
  const [loading, setLoading] = useState(Boolean(supplierId));
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!supplierId) {
      setSupplier(null);
      setLoading(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    const response = await fetchSupplier(supplierId);
    if (response.ok) {
      setSupplier(response.data);
    } else {
      setSupplier(null);
      setError(response.error);
    }
    setLoading(false);
  }, [supplierId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { supplier, loading, error, reload };
}