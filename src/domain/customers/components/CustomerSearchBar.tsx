/** Debounced search input for customer list. */

import { useEffect, useRef, useState } from "react";
import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";

interface Props {
  onSearch: (query: string) => void;
  debounceMs?: number;
  resetSignal?: number;
}

export function CustomerSearchBar({ onSearch, debounceMs = 300, resetSignal = 0 }: Props) {
  const [value, setValue] = useState("");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setValue("");
  }, [resetSignal]);

  useEffect(() => {
    let cancelled = false;

    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      if (!cancelled) {
        onSearch(value);
      }
    }, debounceMs);

    return () => {
      cancelled = true;
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [value, debounceMs, onSearch]);

  return (
    <div className="relative w-full min-w-[16rem] max-w-md">
      <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        type="text"
        placeholder="Search by name or BAN..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        aria-label="Search customers"
        className="pl-9"
      />
    </div>
  );
}
