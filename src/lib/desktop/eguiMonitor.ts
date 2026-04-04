import type {
  InvoiceEguiStatus,
  InvoiceEguiSubmission,
  InvoiceResponse,
} from "../../domain/invoices/types";
import type { DesktopNotificationRequest } from "./notifications";

export const DESKTOP_EGUI_STORAGE_KEY = "ultrerp_desktop_egui_watch_v1";
const MAX_TRACKED_INVOICES = 25;
const NOTIFIABLE_STATUSES = new Set<InvoiceEguiStatus>([
  "SENT",
  "ACKED",
  "FAILED",
  "RETRYING",
  "DEAD_LETTER",
]);

export const DESKTOP_EGUI_POLL_INTERVAL_MS = 30_000;

export interface TrackedEguiInvoice {
  invoiceId: string;
  invoiceNumber: string;
  lastSeenStatus: InvoiceEguiStatus;
  lastNotifiedStatus?: InvoiceEguiStatus;
  updatedAt: string;
}

type TrackedEguiInvoiceMap = Record<string, TrackedEguiInvoice>;

type TrackableInvoice = Pick<InvoiceResponse, "id" | "invoice_number" | "egui_submission">;

export interface RunDesktopEguiNotificationCycleOptions {
  isWindowVisible: () => Promise<boolean>;
  refreshInvoiceStatus: (
    invoiceId: string,
  ) => Promise<Pick<InvoiceEguiSubmission, "status">>;
  notify: (
    notification: DesktopNotificationRequest,
  ) => Promise<{ delivered: boolean }>;
  onError?: (message: string, error: unknown) => void;
  now?: () => string;
}

function readTrackedInvoices(): TrackedEguiInvoiceMap {
  if (typeof window === "undefined") {
    return {};
  }

  const raw = localStorage.getItem(DESKTOP_EGUI_STORAGE_KEY);
  if (!raw) {
    return {};
  }

  try {
    const parsed = JSON.parse(raw) as TrackedEguiInvoiceMap;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeTrackedInvoices(state: TrackedEguiInvoiceMap): void {
  if (typeof window === "undefined") {
    return;
  }

  localStorage.setItem(DESKTOP_EGUI_STORAGE_KEY, JSON.stringify(pruneTrackedInvoices(state)));
}

function pruneTrackedInvoices(state: TrackedEguiInvoiceMap): TrackedEguiInvoiceMap {
  const entries = Object.entries(state)
    .sort(([, left], [, right]) => right.updatedAt.localeCompare(left.updatedAt))
    .slice(0, MAX_TRACKED_INVOICES);
  return Object.fromEntries(entries);
}

export function shouldNotifyEguiTransition(
  previousStatus: InvoiceEguiStatus | null | undefined,
  nextStatus: InvoiceEguiStatus,
): boolean {
  return Boolean(
    previousStatus
      && previousStatus !== nextStatus
      && NOTIFIABLE_STATUSES.has(nextStatus),
  );
}

export function rememberTrackedEguiInvoice(invoice: TrackableInvoice): void {
  if (!invoice.egui_submission) {
    return;
  }

  const state = readTrackedInvoices();
  const existing = state[invoice.id];
  state[invoice.id] = {
    invoiceId: invoice.id,
    invoiceNumber: invoice.invoice_number,
    lastSeenStatus: invoice.egui_submission.status,
    lastNotifiedStatus: existing?.lastNotifiedStatus,
    updatedAt: new Date().toISOString(),
  };
  writeTrackedInvoices(state);
}

export function buildEguiTransitionNotification(
  invoiceNumber: string,
  previousStatus: InvoiceEguiStatus,
  nextStatus: InvoiceEguiStatus,
): DesktopNotificationRequest {
  return {
    title: `Invoice ${invoiceNumber} eGUI ${nextStatus}`,
    body: `UltrERP detected a meaningful eGUI transition from ${previousStatus} to ${nextStatus}.`,
  };
}

export async function runDesktopEguiNotificationCycle(
  options: RunDesktopEguiNotificationCycleOptions,
): Promise<void> {
  if (await options.isWindowVisible()) {
    return;
  }

  const state = readTrackedInvoices();
  const trackedInvoices = Object.values(state);
  if (trackedInvoices.length === 0) {
    return;
  }

  const now = options.now ?? (() => new Date().toISOString());
  let changed = false;

  for (const trackedInvoice of trackedInvoices) {
    try {
      const submission = await options.refreshInvoiceStatus(trackedInvoice.invoiceId);
      const nextStatus = submission.status;
      if (nextStatus === trackedInvoice.lastSeenStatus) {
        continue;
      }

      const previousStatus = trackedInvoice.lastSeenStatus;
      const nextTrackedInvoice: TrackedEguiInvoice = {
        ...trackedInvoice,
        lastSeenStatus: nextStatus,
        updatedAt: now(),
      };

      if (
        shouldNotifyEguiTransition(previousStatus, nextStatus)
        && trackedInvoice.lastNotifiedStatus !== nextStatus
      ) {
        const result = await options.notify(
          buildEguiTransitionNotification(
            trackedInvoice.invoiceNumber,
            previousStatus,
            nextStatus,
          ),
        );
        if (result.delivered) {
          nextTrackedInvoice.lastNotifiedStatus = nextStatus;
        }
      }

      state[trackedInvoice.invoiceId] = nextTrackedInvoice;
      changed = true;
    } catch (error) {
      options.onError?.(
        `Failed to refresh tracked eGUI state for invoice ${trackedInvoice.invoiceId}.`,
        error,
      );
    }
  }

  if (changed) {
    writeTrackedInvoices(state);
  }
}