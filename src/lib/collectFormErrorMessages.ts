import type { FieldErrors, FieldValues } from "react-hook-form";

function collectMessages(value: unknown, messages: string[]) {
  if (!value || typeof value !== "object") {
    return;
  }

  if (Array.isArray(value)) {
    value.forEach((item) => collectMessages(item, messages));
    return;
  }

  const candidate = value as { message?: unknown };
  if (typeof candidate.message === "string" && candidate.message.length > 0) {
    messages.push(candidate.message);
    return;
  }

  Object.values(value as Record<string, unknown>).forEach((nested) => {
    collectMessages(nested, messages);
  });
}

export function collectFormErrorMessages<TFieldValues extends FieldValues>(
  errors: FieldErrors<TFieldValues>,
): string[] {
  const messages: string[] = [];
  collectMessages(errors, messages);
  return Array.from(new Set(messages));
}

export function collectIssueMessages(
  issues: Array<{ message?: string | null | undefined }>,
): string[] {
  return Array.from(
    new Set(
      issues
        .map((issue) => issue.message)
        .filter((message): message is string => typeof message === "string" && message.length > 0),
    ),
  );
}