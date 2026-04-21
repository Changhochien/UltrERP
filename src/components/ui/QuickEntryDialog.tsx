import * as React from "react";

import { cn } from "@/lib/utils";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "./dialog";

const dialogWidthClasses = {
  sm: "sm:max-w-sm",
  md: "sm:max-w-xl",
  lg: "sm:max-w-2xl",
} as const;

export interface QuickEntryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: React.ReactNode;
  description?: React.ReactNode;
  children: React.ReactNode;
  size?: keyof typeof dialogWidthClasses;
  busy?: boolean;
  className?: string;
}

export function QuickEntryDialog({
  busy = false,
  children,
  className,
  description,
  onOpenChange,
  open,
  size = "md",
  title,
}: QuickEntryDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={cn(
          "max-h-[min(85vh,48rem)] overflow-y-auto",
          dialogWidthClasses[size],
          className,
        )}
        aria-busy={busy || undefined}
      >
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description ? <DialogDescription>{description}</DialogDescription> : null}
        </DialogHeader>
        {children}
      </DialogContent>
    </Dialog>
  );
}