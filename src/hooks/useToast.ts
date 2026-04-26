import { useToastContext } from "../providers/ToastProvider";

/**
 * Hook for toast notifications.
 * Returns the toast context with convenience methods.
 * 
 * Usage:
 *   const { success, error, warning, info, toast } = useToast();
 *   success("Operation completed");
 *   error("Something went wrong");
 */
export function useToast() {
  return useToastContext();
}
