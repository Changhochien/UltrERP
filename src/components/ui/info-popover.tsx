/**
 * InfoPopover — a small info-icon trigger that opens a popover with rich content.
 * Reusable across the app for explaining form fields, parameters, and formulas.
 *
 * Usage:
 *   <InfoPopover title="Safety Factor" formula="Safety Stock = Avg × Factor × Lead Time">
 *     Add extra buffer stock to protect against demand spikes or supply delays.
 *   </InfoPopover>
 */

import { Info } from "lucide-react";
import { useTranslation } from "react-i18next";

import {
  Popover,
  PopoverContent,
  PopoverHeader,
  PopoverTitle,
  PopoverDescription,
  PopoverTrigger,
} from "@/components/ui/popover";

interface InfoPopoverProps {
  /** Short label shown as the popover title. */
  title: string;
  /**
   * Child content rendered inside the popover body, below the title.
   */
  children: React.ReactNode;
  /**
   * Optional one-line formula shown below the description in monospace.
   */
  formula?: string;
  /**
   * Icon component from lucide-react. Defaults to Info.
   */
  icon?: React.ComponentType<{ className?: string }>;
  /** Additional className for the trigger button. */
  triggerClassName?: string;
  /** Always show the icon (default: show only on hover/focus). */
  alwaysVisible?: boolean;
}

function InfoPopover({
  title,
  children,
  formula,
  icon: Icon = Info,
  triggerClassName,
  alwaysVisible = false,
}: InfoPopoverProps) {
  const { t } = useTranslation("common", { keyPrefix: "infoPopover" });

  const triggerClasses = alwaysVisible
    ? "inline-flex items-center justify-center text-muted-foreground hover:text-foreground focus-visible:outline-none"
    : "inline-flex items-center justify-center text-muted-foreground opacity-0 transition-opacity hover:text-foreground focus-visible:opacity-100 group-hover:opacity-100";

  return (
    <Popover>
      <PopoverTrigger
        nativeButton={false}
        render={
          <span
            aria-label={t("ariaLabel")}
            title={title}
            className={[triggerClasses, triggerClassName ?? ""].join(" ")}
          />
        }
      >
        <Icon className="size-3.5" />
      </PopoverTrigger>
      <PopoverContent sideOffset={6} className="w-72">
        <PopoverHeader>
          <PopoverTitle>{title}</PopoverTitle>
        </PopoverHeader>
        <div className="flex flex-col gap-1.5 text-sm">
          <PopoverDescription>
            <span className="text-sm leading-relaxed">{children}</span>
          </PopoverDescription>
          {formula && (
            <code className="mt-1 block rounded bg-muted px-2 py-1.5 font-mono text-xs text-muted-foreground">
              {formula}
            </code>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}

/**
 * A label + info-popover compound, useful next to form fields.
 * Renders the label text and the InfoPopover inline.
 */
interface LabeledInfoPopoverProps extends InfoPopoverProps {
  label: string;
}

function LabeledInfoPopover({ label, ...infoProps }: LabeledInfoPopoverProps) {
  return (
    <div className="inline-flex items-center gap-1.5">
      <span className="text-sm font-medium">{label}</span>
      <InfoPopover {...infoProps} />
    </div>
  );
}

export { InfoPopover, LabeledInfoPopover };
