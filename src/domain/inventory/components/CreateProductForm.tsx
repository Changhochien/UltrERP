import { createProduct } from "../../../lib/api/inventory";
import { useTranslation } from "react-i18next";
import type { ProductResponse } from "../types";
import { ProductForm } from "./ProductForm";

interface CreateProductFormProps {
  onSuccess: (product: ProductResponse) => void;
  onCancel?: () => void;
}

export function CreateProductForm({ onSuccess, onCancel }: CreateProductFormProps) {
  const { t } = useTranslation("inventory", { keyPrefix: "createProductForm" });

  return (
    <ProductForm
      submitLabel={t("submitLabel")}
      submittingLabel={t("submittingLabel")}
      labels={{
        code: t("codeLabel"),
        name: t("nameLabel"),
        category: t("categoryLabel"),
        categoryPlaceholder: t("categoryPlaceholder"),
        description: t("descriptionLabel"),
        unit: t("unitLabel"),
        unitPlaceholder: t("unitPlaceholder"),
        standardCost: t("standardCostLabel"),
        cancel: t("cancel"),
      }}
      onSuccess={onSuccess}
      onCancel={onCancel}
      onSubmit={async (values) => {
        try {
          const product = await createProduct(values);
          return { ok: true, product };
        } catch (err) {
          return {
            ok: false,
            formError: err instanceof Error ? err.message : t("failed"),
          };
        }
      }}
    />
  );
}
