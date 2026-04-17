import { ActiveFilterChip } from "./ActiveFilterChip";

export interface ActiveFilter {
  key: string;
  label: string;
  value?: string;
}

interface ActiveFilterBarProps {
  filters: ActiveFilter[];
  onDismiss: (key: string) => void;
  onClearAll: () => void;
}

export function ActiveFilterBar({ filters, onDismiss, onClearAll }: ActiveFilterBarProps) {
  if (filters.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {filters.map((filter) => (
        <ActiveFilterChip
          key={filter.key}
          label={filter.label}
          onDismiss={() => onDismiss(filter.key)}
        />
      ))}
      {filters.length >= 2 && (
        <button
          type="button"
          onClick={onClearAll}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Clear all
        </button>
      )}
    </div>
  );
}