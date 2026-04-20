import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { AnimatePresence } from "framer-motion";

import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastPrimitive,
  ToastTitle,
  ToastViewport,
  type ToastVariant,
} from "@/components/ui/Toast";

const DEFAULT_DURATION = 5000;
const MAX_TOASTS = 5;
const EXIT_DURATION_MS = 180;

export interface ToastInput {
  title: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
}

interface ToastRecord {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
  duration: number;
  open: boolean;
}

export interface ToastContextValue {
  toast: (input: ToastInput) => string;
  success: (title: string, description?: string, duration?: number) => string;
  error: (title: string, description?: string, duration?: number) => string;
  warning: (title: string, description?: string, duration?: number) => string;
  info: (title: string, description?: string, duration?: number) => string;
  dismiss: (id?: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

function createToastId() {
  return `toast-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);
  const dismissTimersRef = useRef<Record<string, number>>({});

  useEffect(() => {
    return () => {
      Object.values(dismissTimersRef.current).forEach((timer) => {
        window.clearTimeout(timer);
      });
    };
  }, []);

  const removeToast = useCallback((id: string) => {
    const timer = dismissTimersRef.current[id];
    if (timer) {
      window.clearTimeout(timer);
      delete dismissTimersRef.current[id];
    }
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const dismiss = useCallback((id?: string) => {
    if (!id) {
      const currentIds = toasts.map((toast) => toast.id);
      setToasts((current) => current.map((toast) => ({ ...toast, open: false })));
      currentIds.forEach((toastId) => {
        dismissTimersRef.current[toastId] = window.setTimeout(() => {
          removeToast(toastId);
        }, EXIT_DURATION_MS);
      });
      return;
    }

    setToasts((current) =>
      current.map((toast) => (toast.id === id ? { ...toast, open: false } : toast)),
    );
    dismissTimersRef.current[id] = window.setTimeout(() => {
      removeToast(id);
    }, EXIT_DURATION_MS);
  }, [removeToast, toasts]);

  const handleOpenChange = useCallback((id: string, open: boolean) => {
    if (open) {
      return;
    }
    dismiss(id);
  }, [dismiss]);

  const toast = useCallback((input: ToastInput) => {
    const id = createToastId();
    const nextToast: ToastRecord = {
      id,
      title: input.title,
      description: input.description,
      variant: input.variant ?? "info",
      duration: input.duration ?? DEFAULT_DURATION,
      open: true,
    };

    setToasts((current) => [nextToast, ...current].slice(0, MAX_TOASTS));
    return id;
  }, []);

  const contextValue = useMemo<ToastContextValue>(() => ({
    toast,
    success: (title, description, duration) => toast({ title, description, duration, variant: "success" }),
    error: (title, description, duration) => toast({ title, description, duration, variant: "destructive" }),
    warning: (title, description, duration) => toast({ title, description, duration, variant: "warning" }),
    info: (title, description, duration) => toast({ title, description, duration, variant: "info" }),
    dismiss,
  }), [dismiss, toast]);

  return (
    <ToastContext.Provider value={contextValue}>
      <ToastPrimitive.Provider duration={DEFAULT_DURATION} swipeDirection="right">
        {children}
        <AnimatePresence initial={false}>
          {toasts.map((item) => (
            <Toast
              key={item.id}
              open={item.open}
              onOpenChange={(open) => handleOpenChange(item.id, open)}
              duration={item.duration}
              variant={item.variant}
              type={item.variant === "destructive" ? "foreground" : "background"}
            >
              <div className="space-y-1.5 pr-2">
                <ToastTitle>{item.title}</ToastTitle>
                {item.description ? <ToastDescription>{item.description}</ToastDescription> : null}
              </div>
              <ToastClose aria-label="Dismiss notification" />
            </Toast>
          ))}
        </AnimatePresence>
        <ToastViewport />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  );
}

export function useToastContext() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider.");
  }
  return context;
}