import { useCallback, useEffect, useMemo, useState } from "react";

import type { CRMSetupBundle } from "../types";
import { getCRMSetupBundle } from "../../../lib/api/crm";

const FALLBACK_SETUP_BUNDLE: CRMSetupBundle = {
  settings: {
    lead_duplicate_policy: "block",
    contact_creation_enabled: true,
    default_quotation_validity_days: 30,
    carry_forward_communications: true,
    carry_forward_comments: true,
    opportunity_auto_close_days: null,
  },
  sales_stages: [
    { id: "default-qualification", name: "qualification", probability: 10, sort_order: 10, is_active: true },
    { id: "default-proposal", name: "proposal", probability: 50, sort_order: 20, is_active: true },
    { id: "default-negotiation", name: "negotiation", probability: 75, sort_order: 30, is_active: true },
    { id: "default-commitment", name: "commitment", probability: 90, sort_order: 40, is_active: true },
  ],
  territories: [
    { id: "default-north", name: "North", parent_id: null, is_group: false, sort_order: 10, is_active: true },
    { id: "default-taipei", name: "Taipei", parent_id: null, is_group: false, sort_order: 20, is_active: true },
    { id: "default-central", name: "Central", parent_id: null, is_group: false, sort_order: 30, is_active: true },
    { id: "default-south", name: "South", parent_id: null, is_group: false, sort_order: 40, is_active: true },
  ],
  customer_groups: [
    { id: "default-industrial", name: "Industrial", parent_id: null, is_group: false, sort_order: 10, is_active: true },
    { id: "default-dealer", name: "Dealer", parent_id: null, is_group: false, sort_order: 20, is_active: true },
    { id: "default-end-user", name: "End User", parent_id: null, is_group: false, sort_order: 30, is_active: true },
  ],
};

export function useCRMSetupBundle() {
  const [data, setData] = useState<CRMSetupBundle>(FALLBACK_SETUP_BUNDLE);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadBundle = useCallback(() => {
    let cancelled = false;
    setLoading(true);
    getCRMSetupBundle()
      .then((bundle) => {
        if (!cancelled) {
          setData(bundle);
          setError(null);
        }
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load CRM setup.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => loadBundle(), [loadBundle]);

  const salesStageOptions = useMemo(
    () => data.sales_stages.filter((item) => item.is_active).sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name)),
    [data.sales_stages],
  );
  const territoryOptions = useMemo(
    () => data.territories.filter((item) => item.is_active).sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name)),
    [data.territories],
  );
  const customerGroupOptions = useMemo(
    () => data.customer_groups.filter((item) => item.is_active).sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name)),
    [data.customer_groups],
  );

  return {
    data,
    loading,
    error,
    reload: loadBundle,
    salesStageOptions,
    territoryOptions,
    customerGroupOptions,
  };
}
