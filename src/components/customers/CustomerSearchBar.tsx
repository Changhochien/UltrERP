/** Debounced search input for customer list. */

import { useEffect, useRef, useState } from "react";

interface Props {
  onSearch: (query: string) => void;
  debounceMs?: number;
}

export function CustomerSearchBar({ onSearch, debounceMs = 300 }: Props) {
  const [value, setValue] = useState("");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => onSearch(value), debounceMs);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [value, debounceMs, onSearch]);

  return (
    <input
      type="text"
      className="search-input"
      placeholder="Search by name or BAN..."
      value={value}
      onChange={(e) => setValue(e.target.value)}
      aria-label="Search customers"
    />
  );
}
