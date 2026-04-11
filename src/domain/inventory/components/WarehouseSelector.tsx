/** Warehouse selector dropdown — for global nav or scoped use. */

import { SurfaceMessage } from "../../../components/layout/PageLayout";
import { Skeleton } from "../../../components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../../components/ui/select";
import type { Warehouse } from "../types";
import { useWarehouses } from "../hooks/useWarehouses";
import { useTranslation } from "react-i18next";

interface Props {
  value: Warehouse | null;
  onChange: (warehouse: Warehouse | null) => void;
  /** If true, shows an "All Warehouses" option. */
  allowAll?: boolean;
  label?: string;
}

export function WarehouseSelector({
  value,
  onChange,
  allowAll = true,
  label,
}: Props) {
  const { t } = useTranslation("common", { keyPrefix: "inventory.warehouseSelector" });
  const { warehouses, loading, error } = useWarehouses();

  if (loading) return <Skeleton className="h-10 w-full sm:w-72" />;
  if (error) return <SurfaceMessage tone="danger">{error}</SurfaceMessage>;

  const handleChange = (nextValue: string) => {
    if (nextValue === "all") {
      onChange(null);
      return;
    }

    const warehouse = warehouses.find((item) => item.id === nextValue) ?? null;
    onChange(warehouse);
  };

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-foreground">{label ?? t("label")}</label>
      <Select value={value?.id ?? (allowAll ? "all" : undefined)} onValueChange={handleChange}>
        <SelectTrigger className="w-full sm:w-72">
          <SelectValue placeholder={t("selectWarehouse")} />
        </SelectTrigger>
        <SelectContent>
          {allowAll ? <SelectItem value="all">{t("allWarehouses")}</SelectItem> : null}
          {warehouses.map((wh) => (
            <SelectItem key={wh.id} value={wh.id}>
              {wh.name} ({wh.code})
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
