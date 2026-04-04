import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { useMemo, useState, type KeyboardEvent, type ReactNode } from "react";

import { cn } from "../../lib/utils";
import { Button } from "../ui/button";
import { Skeleton } from "../ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";

export type DataTableSortDirection = "asc" | "desc";

export interface DataTableSortState {
  columnId: string;
  direction: DataTableSortDirection;
}

export interface DataTableColumn<TData> {
  id: string;
  header: string;
  cell: (row: TData) => ReactNode;
  sortable?: boolean;
  getSortValue?: (row: TData) => string | number | null | undefined;
  className?: string;
  headerClassName?: string;
}

interface DataTableProps<TData> {
  columns: DataTableColumn<TData>[];
  data: TData[];
  toolbar?: ReactNode;
  summary?: ReactNode;
  loading?: boolean;
  error?: ReactNode;
  emptyTitle?: string;
  emptyDescription?: string;
  loadingRowCount?: number;
  page?: number;
  pageSize?: number;
  totalItems?: number;
  onPageChange?: (page: number) => void;
  sortState?: DataTableSortState | null;
  onSortChange?: (next: DataTableSortState) => void;
  onRowClick?: (row: TData) => void;
  getRowId?: (row: TData) => string;
  rowLabel?: (row: TData) => string;
  getRowClassName?: (row: TData) => string | undefined;
}

function compareValues(
  left: string | number | null | undefined,
  right: string | number | null | undefined,
): number {
  if (left == null && right == null) {
    return 0;
  }

  if (left == null) {
    return 1;
  }

  if (right == null) {
    return -1;
  }

  if (typeof left === "number" && typeof right === "number") {
    return left - right;
  }

  return String(left).localeCompare(String(right), undefined, { numeric: true, sensitivity: "base" });
}

export function DataTableToolbar({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("flex flex-col gap-3 border-b border-border/70 pb-4 md:flex-row md:items-center md:justify-between", className)}>{children}</div>;
}

export function DataTable<TData>({
  columns,
  data,
  toolbar,
  summary,
  loading = false,
  error,
  emptyTitle = "No records found",
  emptyDescription = "Adjust the filters or try again later.",
  loadingRowCount = 6,
  page,
  pageSize,
  totalItems,
  onPageChange,
  sortState,
  onSortChange,
  onRowClick,
  getRowId,
  rowLabel,
  getRowClassName,
}: DataTableProps<TData>) {
  const [internalSortState, setInternalSortState] = useState<DataTableSortState | null>(null);
  const activeSortState = sortState ?? internalSortState;
  const isManualSorting = Boolean(sortState && onSortChange);

  const rows = useMemo(() => {
    if (isManualSorting || !activeSortState) {
      return data;
    }

    const column = columns.find((item) => item.id === activeSortState.columnId);
    if (!column?.getSortValue) {
      return data;
    }

    const sorted = [...data].sort((left, right) => compareValues(column.getSortValue?.(left), column.getSortValue?.(right)));
    return activeSortState.direction === "desc" ? sorted.reverse() : sorted;
  }, [activeSortState, columns, data, isManualSorting]);

  const canPreviousPage = Boolean(onPageChange && page && page > 1);
  const canNextPage = Boolean(
    onPageChange
      && page
      && pageSize
      && totalItems != null
      && page * pageSize < totalItems,
  );
  const pageStart = page && pageSize && totalItems != null && totalItems > 0
    ? (page - 1) * pageSize + 1
    : 0;
  const pageEnd = page && pageSize && totalItems != null && totalItems > 0
    ? Math.min(page * pageSize, totalItems)
    : 0;
  const totalPages = pageSize && totalItems != null && totalItems > 0
    ? Math.ceil(totalItems / pageSize)
    : 1;

  const handleSort = (column: DataTableColumn<TData>) => {
    const currentDirection = activeSortState?.columnId === column.id ? activeSortState.direction : null;
    const nextState: DataTableSortState = {
      columnId: column.id,
      direction: currentDirection === "asc" ? "desc" : "asc",
    };

    if (onSortChange) {
      onSortChange(nextState);
      return;
    }

    setInternalSortState(nextState);
  };

  const handleRowKeyDown = (event: KeyboardEvent<HTMLTableRowElement>, row: TData) => {
    if (!onRowClick) {
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onRowClick(row);
    }
  };

  return (
    <div className="space-y-4">
      {toolbar}

      {summary ? <div className="text-sm text-muted-foreground">{summary}</div> : null}

      {error ? (
        <div role="alert" className="rounded-xl border border-destructive/20 bg-destructive/8 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      <div className="overflow-hidden rounded-2xl border border-border/80 bg-card/90 shadow-sm">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/35 hover:bg-muted/35">
              {columns.map((column) => {
                const isActiveSort = activeSortState?.columnId === column.id;
                const isSortable = column.sortable ?? Boolean(column.getSortValue || onSortChange);
                const SortIcon = !isActiveSort ? ArrowUpDown : activeSortState?.direction === "asc" ? ArrowUp : ArrowDown;

                return (
                  <TableHead
                    key={column.id}
                    className={column.headerClassName}
                    aria-sort={isActiveSort ? (activeSortState?.direction === "asc" ? "ascending" : "descending") : undefined}
                  >
                    {isSortable ? (
                      <button
                        type="button"
                        className={cn(
                          "group flex h-auto w-full items-center justify-between gap-2 rounded-none border-0 bg-transparent px-0 py-0 text-left text-xs font-semibold uppercase tracking-[0.18em] shadow-none outline-none transition-colors hover:bg-transparent focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-0",
                          isActiveSort
                            ? "text-foreground"
                            : "text-muted-foreground hover:text-foreground",
                        )}
                        onClick={() => handleSort(column)}
                      >
                        <span className="truncate">{column.header}</span>
                        <SortIcon
                          aria-hidden="true"
                          className={cn(
                            "size-3.5 shrink-0 transition-colors",
                            isActiveSort
                              ? "text-primary"
                              : "text-muted-foreground/70 group-hover:text-foreground",
                          )}
                        />
                      </button>
                    ) : (
                      column.header
                    )}
                  </TableHead>
                );
              })}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading
              ? Array.from({ length: loadingRowCount }, (_, index) => (
                  <TableRow key={`loading-${index}`}>
                    {columns.map((column) => (
                      <TableCell key={`${column.id}-${index}`} className={column.className}>
                        <Skeleton className="h-5 w-full" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              : rows.length === 0
                ? (
                    <TableRow className="hover:bg-transparent">
                      <TableCell colSpan={columns.length} className="px-6 py-10 text-center">
                        <div className="space-y-1.5">
                          <p className="text-sm font-medium text-foreground">{emptyTitle}</p>
                          <p className="text-sm text-muted-foreground">{emptyDescription}</p>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                : rows.map((row, rowIndex) => (
                    <TableRow
                      key={getRowId ? getRowId(row) : rowIndex}
                      className={cn(
                        onRowClick && "cursor-pointer focus-visible:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring/40",
                        getRowClassName?.(row),
                      )}
                      role={onRowClick ? "button" : undefined}
                      tabIndex={onRowClick ? 0 : undefined}
                      aria-label={onRowClick ? rowLabel?.(row) : undefined}
                      onClick={onRowClick ? () => onRowClick(row) : undefined}
                      onKeyDown={(event) => handleRowKeyDown(event, row)}
                    >
                      {columns.map((column) => (
                        <TableCell key={column.id} className={column.className}>
                          {column.cell(row)}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
          </TableBody>
        </Table>
      </div>

      {page && pageSize && totalItems != null && onPageChange ? (
        <div className="flex flex-col gap-3 border-t border-border/70 pt-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span aria-live="polite" className="tabular-nums">
            Showing {pageStart.toLocaleString()}-{pageEnd.toLocaleString()} of {totalItems.toLocaleString()}
            <span className="hidden sm:inline"> · Page {page} of {totalPages.toLocaleString()}</span>
          </span>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              aria-label={`Go to previous page${page > 1 ? `, page ${(page - 1).toLocaleString()}` : ""}`}
              disabled={!canPreviousPage || loading}
              onClick={() => onPageChange(page - 1)}
            >
              Previous
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              aria-label={`Go to next page${page < totalPages ? `, page ${(page + 1).toLocaleString()}` : ""}`}
              disabled={!canNextPage || loading}
              onClick={() => onPageChange(page + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}