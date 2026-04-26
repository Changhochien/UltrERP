import * as React from "react";
import * as ToastPrimitive from "@radix-ui/react-toast";
import { motion } from "framer-motion";
import { X } from "lucide-react";
import { cva, type VariantProps } from "class-variance-authority";
import { createPortal } from "react-dom";

import { cn } from "@/lib/utils";

const toastVariants = cva(
  "pointer-events-auto relative overflow-hidden rounded-[1.35rem] border bg-card/96 px-4 py-3 pr-11 shadow-[0_28px_70px_-38px_rgba(15,23,42,0.58)] backdrop-blur-xl",
  {
    variants: {
      variant: {
        success: "tone-success",
        destructive: "tone-destructive",
        warning: "tone-warning",
        info: "tone-info",
      },
    },
    defaultVariants: {
      variant: "info",
    },
  },
);

export type ToastVariant = NonNullable<VariantProps<typeof toastVariants>["variant"]>;

export interface ToastProps
  extends React.ComponentPropsWithoutRef<typeof ToastPrimitive.Root>,
    VariantProps<typeof toastVariants> {}

const Toast = React.forwardRef<
  React.ElementRef<typeof ToastPrimitive.Root>,
  ToastProps
>(({ className, variant, children, ...props }, ref) => (
  <motion.div
    layout
    initial={{ opacity: 0, y: 24, scale: 0.96 }}
    animate={{ opacity: 1, y: 0, scale: 1 }}
    exit={{ opacity: 0, y: 12, scale: 0.98 }}
    transition={{ duration: 0.18, ease: "easeOut" }}
  >
    <ToastPrimitive.Root
      ref={ref}
      className={cn(toastVariants({ variant }), className)}
      {...props}
    >
      {children}
    </ToastPrimitive.Root>
  </motion.div>
));

Toast.displayName = ToastPrimitive.Root.displayName;

const ToastTitle = React.forwardRef<
  React.ElementRef<typeof ToastPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Title>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Title
    ref={ref}
    className={cn("text-sm font-semibold tracking-tight", className)}
    {...props}
  />
));

ToastTitle.displayName = ToastPrimitive.Title.displayName;

const ToastDescription = React.forwardRef<
  React.ElementRef<typeof ToastPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Description>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Description
    ref={ref}
    className={cn("text-sm leading-5 opacity-90", className)}
    {...props}
  />
));

ToastDescription.displayName = ToastPrimitive.Description.displayName;

const ToastClose = React.forwardRef<
  React.ElementRef<typeof ToastPrimitive.Close>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Close>
>(({ className, children, ...props }, ref) => (
  <ToastPrimitive.Close
    ref={ref}
    className={cn(
      "absolute right-2 top-2 inline-flex size-8 items-center justify-center rounded-full border border-transparent text-current/70 transition-colors hover:bg-black/6 hover:text-current focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background dark:hover:bg-white/8",
      className,
    )}
    toast-close=""
    {...props}
  >
    {children ?? <X className="size-4" aria-hidden="true" />}
  </ToastPrimitive.Close>
));

ToastClose.displayName = ToastPrimitive.Close.displayName;

function ToastViewport({ className, ...props }: React.ComponentPropsWithoutRef<typeof ToastPrimitive.Viewport>) {
  if (typeof document === "undefined") {
    return null;
  }

  return createPortal(
    <ToastPrimitive.Viewport
      className={cn(
        "fixed bottom-4 right-4 z-[120] flex w-[min(26rem,calc(100vw-2rem))] max-w-full flex-col-reverse gap-3 outline-none sm:bottom-6 sm:right-6",
        className,
      )}
      {...props}
    />,
    document.body,
  );
}

/**
 * ToastService - Static service for showing toast notifications.
 * Use this for non-hook contexts or when you need a simple API.
 */
export const ToastService = {
  success: (title: string, description?: string) => {
    // Dispatch custom event that ToastProvider listens to
    window.dispatchEvent(
      new CustomEvent("toast", {
        detail: { title, description, variant: "success" },
      })
    );
    return title;
  },
  error: (title: string, description?: string) => {
    window.dispatchEvent(
      new CustomEvent("toast", {
        detail: { title, description, variant: "destructive" },
      })
    );
    return title;
  },
  warning: (title: string, description?: string) => {
    window.dispatchEvent(
      new CustomEvent("toast", {
        detail: { title, description, variant: "warning" },
      })
    );
    return title;
  },
  info: (title: string, description?: string) => {
    window.dispatchEvent(
      new CustomEvent("toast", {
        detail: { title, description, variant: "info" },
      })
    );
    return title;
  },
};

export {
  Toast,
  ToastClose,
  ToastDescription,
  ToastPrimitive,
  ToastTitle,
  ToastViewport,
};
