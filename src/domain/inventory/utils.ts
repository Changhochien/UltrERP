export function getStatusVariant(
  stock: number,
  reorderPoint: number,
  productStatus: string,
): "healthy" | "warning" | "critical" | "inactive" {
  if (productStatus !== "active") return "inactive";
  if (stock === 0) return "critical";
  if (stock < reorderPoint * 0.5) return "critical";
  if (stock < reorderPoint) return "warning";
  return "healthy";
}
