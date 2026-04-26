/**
 * Hook for displaying API errors as toast notifications.
 */

import { useCallback } from "react";
import { ApiError } from "@/lib/api/errors";

/**
 * Hook that returns a function to display API errors as toast notifications.
 */
export function useApiErrorToast() {
  const handleError = useCallback((error: unknown, defaultMessage?: string) => {
    let message = defaultMessage ?? "An error occurred";

    if (error instanceof ApiError) {
      if (typeof error.detail === "string") {
        message = error.detail;
      } else if (error.detail?.errors && error.detail.errors.length > 0) {
        message = error.detail.errors.map((e) => e.message).join(", ");
      } else if (error.detail?.message) {
        message = error.detail.message;
      }
    } else if (error instanceof Error) {
      message = error.message;
    }

    // Use window.dispatchEvent for ToastService compatibility
    window.dispatchEvent(
      new CustomEvent("toast", {
        detail: {
          title: message,
          variant: "destructive" as const,
        },
      })
    );
  }, []);

  return handleError;
}
