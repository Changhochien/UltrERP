import { X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface ActiveFilterChipProps {
  label: string;
  onDismiss: () => void;
}

export function ActiveFilterChip({ label, onDismiss }: ActiveFilterChipProps) {
  return (
    <Badge variant="secondary" className="gap-1.5 pl-2 pr-1">
      <span>{label}</span>
      <Button
        type="button"
        variant="ghost"
        size="icon-xs"
        onClick={onDismiss}
        aria-label={`Remove ${label} filter`}
        className="ml-0.5 size-4 p-0"
      >
        <X className="size-3" />
      </Button>
    </Badge>
  );
}