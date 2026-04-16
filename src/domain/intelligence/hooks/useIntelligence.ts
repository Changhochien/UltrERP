import { useCallback, useEffect, useState } from "react";

import {
  fetchCategoryTrends,
  fetchCustomerBuyingBehavior,
  fetchCustomerProductProfile,
  fetchCustomerRiskSignals,
  fetchMarketOpportunities,
  fetchProspectGaps,
  fetchProductAffinityMap,
  fetchProductPerformance,
  fetchRevenueDiagnosis,
} from "../../../lib/api/intelligence";
import type {
  CategoryTrends,
  CustomerBuyingBehavior,
  CustomerBuyingBehaviorCustomerType,
  CustomerBuyingBehaviorPeriod,
  CustomerProductProfile,
  CustomerRiskSignals,
  MarketOpportunities,
  ProspectGaps,
  ProspectGapCustomerFilter,
  ProductAffinityMap,
  ProductLifecycleStage,
  ProductPerformance,
  RevenueDiagnosis,
  RevenueDiagnosisPeriod,
} from "../types";

export function useCategoryTrends(period: "last_30d" | "last_90d" | "last_12m" = "last_90d") {
  const [data, setData] = useState<CategoryTrends | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const trends = await fetchCategoryTrends(period);
        if (!isActive) return;
        setData(trends);
      } catch (err) {
        if (!isActive) return;
        setError(err instanceof Error ? err.message : "Failed to load category trends");
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    };

    void load();

    return () => {
      isActive = false;
    };
  }, [period]);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const trends = await fetchCategoryTrends(period);
      setData(trends);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load category trends");
    } finally {
      setIsLoading(false);
    }
  }, [period]);

  return { data, isLoading, error, refetch };
}

export function useMarketOpportunities(period: "last_30d" | "last_90d" | "last_12m" = "last_90d") {
  const [data, setData] = useState<MarketOpportunities | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const opportunities = await fetchMarketOpportunities(period);
        if (!isActive) return;
        setData(opportunities);
      } catch (err) {
        if (!isActive) return;
        setError(err instanceof Error ? err.message : "Failed to load market opportunities");
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    };

    void load();

    return () => {
      isActive = false;
    };
  }, [period]);

  return { data, isLoading, error };
}

export function useRevenueDiagnosis(
  period: RevenueDiagnosisPeriod = "1m",
  anchorMonth?: string,
  category?: string,
  limit = 10,
) {
  const [data, setData] = useState<RevenueDiagnosis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const diagnosis = await fetchRevenueDiagnosis(period, anchorMonth, category, limit);
        if (!isActive) return;
        setData(diagnosis);
      } catch (err) {
        if (!isActive) return;
        setError(err instanceof Error ? err.message : "Failed to load revenue diagnosis");
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    };

    void load();

    return () => {
      isActive = false;
    };
  }, [anchorMonth, category, limit, period]);

  return { data, isLoading, error };
}

export function useProductPerformance(
  category?: string,
  lifecycleStage?: ProductLifecycleStage,
  limit = 25,
  includeCurrentMonth = false,
) {
  const [data, setData] = useState<ProductPerformance | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const performance = await fetchProductPerformance(category, lifecycleStage, limit, includeCurrentMonth);
        if (!isActive) return;
        setData(performance);
      } catch (err) {
        if (!isActive) return;
        setError(err instanceof Error ? err.message : "Failed to load product performance");
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    };

    void load();

    return () => {
      isActive = false;
    };
  }, [category, includeCurrentMonth, lifecycleStage, limit]);

  return { data, isLoading, error };
}

export function useProductAffinity(minShared = 2, limit = 50) {
  const [data, setData] = useState<ProductAffinityMap | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const affinityMap = await fetchProductAffinityMap(minShared, limit);
      setData(affinityMap);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load product affinity map");
    } finally {
      setIsLoading(false);
    }
  }, [limit, minShared]);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, isLoading, error, refetch: load };
}

export function useCustomerRiskSignals(
  status: "all" | "growing" | "at_risk" | "dormant" | "new" | "stable" = "all",
  limit = 50,
) {
  const [data, setData] = useState<CustomerRiskSignals | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const riskSignals = await fetchCustomerRiskSignals(status, limit);
        if (!isActive) return;
        setData(riskSignals);
      } catch (err) {
        if (!isActive) return;
        setError(err instanceof Error ? err.message : "Failed to load customer risk signals");
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    };

    void load();

    return () => {
      isActive = false;
    };
  }, [limit, status]);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const riskSignals = await fetchCustomerRiskSignals(status, limit);
      setData(riskSignals);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load customer risk signals");
    } finally {
      setIsLoading(false);
    }
  }, [limit, status]);

  return { data, isLoading, error, refetch };
}

export function useCustomerBuyingBehavior(
  customerType: CustomerBuyingBehaviorCustomerType = "dealer",
  period: CustomerBuyingBehaviorPeriod = "12m",
  limit = 20,
  includeCurrentMonth = false,
) {
  const [data, setData] = useState<CustomerBuyingBehavior | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const behavior = await fetchCustomerBuyingBehavior(customerType, period, limit, includeCurrentMonth);
        if (!isActive) return;
        setData(behavior);
      } catch (err) {
        if (!isActive) return;
        setError(err instanceof Error ? err.message : "Failed to load customer buying behavior");
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    };

    void load();

    return () => {
      isActive = false;
    };
  }, [customerType, includeCurrentMonth, limit, period]);

  return { data, isLoading, error };
}

export function useProspectGaps(
  category: string,
  customerType: ProspectGapCustomerFilter = "dealer",
  limit = 20,
) {
  const [data, setData] = useState<ProspectGaps | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!category.trim()) {
      setData(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    let isActive = true;

    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const gaps = await fetchProspectGaps(category, customerType, limit);
        if (!isActive) return;
        setData(gaps);
      } catch (err) {
        if (!isActive) return;
        setError(err instanceof Error ? err.message : "Failed to load prospect gaps");
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    };

    void load();

    return () => {
      isActive = false;
    };
  }, [category, customerType, limit]);

  const refetch = useCallback(async () => {
    if (!category.trim()) {
      setData(null);
      setError(null);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const gaps = await fetchProspectGaps(category, customerType, limit);
      setData(gaps);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load prospect gaps");
    } finally {
      setIsLoading(false);
    }
  }, [category, customerType, limit]);

  return { data, isLoading, error, refetch };
}

export function useCustomerProductProfile(customerId: string) {
  const [data, setData] = useState<CustomerProductProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const profile = await fetchCustomerProductProfile(customerId);
      setData(profile);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load customer product profile",
      );
    } finally {
      setIsLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, isLoading, error, refetch: load };
}