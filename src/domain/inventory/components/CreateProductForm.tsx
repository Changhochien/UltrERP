import { createProduct } from "../../../lib/api/inventory";
import type { ProductResponse } from "../types";
import { ProductForm } from "./ProductForm";

interface CreateProductFormProps {
  onSuccess: (product: ProductResponse) => void;
  onCancel?: () => void;
}

export function CreateProductForm({ onSuccess, onCancel }: CreateProductFormProps) {
  return (
    <ProductForm
      submitLabel="Create Product"
      submittingLabel="Creating..."
      onSuccess={onSuccess}
      onCancel={onCancel}
      onSubmit={async (values) => {
        try {
          const product = await createProduct(values);
          return { ok: true, product };
        } catch (err) {
          return {
            ok: false,
            formError: err instanceof Error ? err.message : "Failed to create product",
          };
        }
      }}
    />
  );
}
