import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const spinnerVariants = cva(
  "inline-block animate-spin rounded-full border-current border-r-transparent",
  {
    variants: {
      size: {
        sm: "size-3 border-[1.5px]",
        default: "size-4 border-2",
        lg: "size-5 border-[2.5px]",
      },
    },
    defaultVariants: {
      size: "default",
    },
  },
);

export interface SpinnerProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof spinnerVariants> {
  label?: string;
}

export function Spinner({ className, label, size, ...props }: SpinnerProps) {
  const isDecorative = !label;

  return (
    <span
      role={isDecorative ? undefined : "status"}
      aria-label={label}
      aria-hidden={isDecorative ? true : undefined}
      className={cn(spinnerVariants({ size }), className)}
      {...props}
    >
      {label ? <span className="sr-only">{label}</span> : null}
    </span>
  );
}