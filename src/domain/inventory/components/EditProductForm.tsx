import { ProductForm } from "./ProductForm";
import { updateProduct } from "../../../lib/api/inventory";
import type { ProductDetail, ProductResponse } from "../types";

interface EditProductFormProps {
  product: ProductDetail;
  onSuccess: (product: ProductResponse) => void;
  onCancel: () => void;
}

export function EditProductForm({ product, onSuccess, onCancel }: EditProductFormProps) {
  return (
    <ProductForm
      initialValues={{
        code: product.code,
        name: product.name,
        category: product.category ?? "",
        description: product.description ?? "",
        unit: product.unit,
        standard_cost: product.standard_cost ?? "",
      }}
      submitLabel="Save Changes"
      submittingLabel="Saving…"
      onSuccess={onSuccess}
      onCancel={onCancel}
      onSubmit={async (values) => {
        const result = await updateProduct(product.id, values);
        if (result.ok) {
          return { ok: true, product: result.data };
        }
        return { ok: false, fieldErrors: result.errors };
      }}
    />
  );
}