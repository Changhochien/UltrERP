export type AlertSeverity = "CRITICAL" | "WARNING" | "INFO";

export function normalizeAlertSeverity(
  severity: string | null | undefined,
): AlertSeverity {
  switch (severity) {
    case "CRITICAL":
    case "WARNING":
    case "INFO":
      return severity;
    default:
      return "INFO";
  }
}