export function isFeatureDisabledError(error: string | null | undefined): boolean {
  return typeof error === "string" && /\b(?:is|are) disabled\b/i.test(error);
}