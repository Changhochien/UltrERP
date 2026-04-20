import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type PaginationState,
  type RowSelectionState,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { useMemo, useState, type KeyboardEvent, type ReactNode } from "react";

import { cn } from "../../lib/utils";
import { Button } from "../ui/button";
import { Checkbox } from "../ui/checkbox";
import { Skeleton } from "../ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import type { DataTableColumn, DataTableSortState } from "./DataTable";

export interface TanStackBulkActionsContext<TData> {
  selectedRows: TData[];
  clearSelection: () => void;
}

interface TanStackDataTableProps<TData> {
  columns: DataTableColumn<TData>[];
  data: TData[];
  toolbar?: ReactNode;
  filterBar?: ReactNode;
  summary?: ReactNode;
  tableClassName?: string;
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
  onSortChange?: (next: DataTableSortState | null) => void;
  onRowClick?: (row: TData) => void;
  getRowId?: (row: TData) => string;
  rowLabel?: (row: TData) => string;
  getRowClassName?: (row: TData) => string | undefined;
  stickyHeader?: boolean;
  enableColumnResizing?: boolean;
  defaultColumnMinSize?: number;
  enableRowSelection?: boolean;
  renderBulkActions?: (context: TanStackBulkActionsContext<TData>) => ReactNode;
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

function toSortingState(sortState: DataTableSortState | null | undefined): SortingState {
  if (!sortState) {
    return [];
  }

  return [{ id: sortState.columnId, desc: sortState.direction === "desc" }];
}

function getNextSortState(
  currentSortState: DataTableSortState | null | undefined,
  columnId: string,
): DataTableSortState | null {
  if (!currentSortState || currentSortState.columnId !== columnId) {
    return { columnId, direction: "asc" };
  }

  if (currentSortState.direction === "asc") {
    return { columnId, direction: "desc" };
  }

  return null;
}

export function TanStackDataTable<TData>({
  columns,
  data,
  toolbar,
  filterBar,
  summary,
  tableClassName,
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
  stickyHeader = false,
  enableColumnResizing = false,
  defaultColumnMinSize = 120,
  enableRowSelection = false,
  renderBulkActions,
}: TanStackDataTableProps<TData>) {
  const [internalSortState, setInternalSortState] = useState<DataTableSortState | null>(null);
  const [internalPagination, setInternalPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: pageSize ?? 20,
  });
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});

  const activeSortState = sortState !== undefined ? sortState : internalSortState;
  const controlledPagination = page != null && pageSize != null && typeof onPageChange === "function";
  const manualPagination = controlledPagination && totalItems != null;
  const internalPaginationEnabled = !controlledPagination && pageSize != null;

  const columnDefs = useMemo<ColumnDef<TData>[]>(() => {
    const mappedColumns = columns.map<ColumnDef<TData>>((column) => ({
      id: column.id,
      accessorFn: (row) => row,
      header: () => column.header,
      cell: (info) => {
        const row = info.row.original;
        if (column.onClick) {
          return <div onClick={(event) => column.onClick?.(event, row)}>{column.cell(row)}</div>;
        }

        return column.cell(row);
      },
      enableSorting: column.sortable ?? Boolean(column.getSortValue || onSortChange),
      sortingFn: column.getSortValue
        ? (left, right) => compareValues(column.getSortValue?.(left.original), column.getSortValue?.(right.original))
        : undefined,
      enableResizing: enableColumnResizing && (column.enableResizing ?? true),
      size: column.size,
      minSize: column.minSize ?? defaultColumnMinSize,
      meta: {
        className: column.className,
        headerClassName: column.headerClassName,
      },
    }));

    if (!enableRowSelection) {
      return mappedColumns;
    }

    return [
      {
        id: "__select__",
        header: ({ table }) => {
          const checked = table.getIsAllRowsSelected()
            ? true
            : table.getIsSomeRowsSelected()
              ? "mixed"
              : false;

          return (
            <div className="flex items-center justify-center" onClick={(event) => event.stopPropagation()}>
              <Checkbox
                aria-label="Select all rows"
                checked={checked}
                onCheckedChange={(value) => table.toggleAllRowsSelected(Boolean(value))}
              />
            </div>
          );
        },
        cell: ({ row }) => {
          const label = rowLabel
            ? `Select ${rowLabel(row.original)}`
            : `Select row ${row.index + 1}`;
          return (
            <div className="flex items-center justify-center" onClick={(event) => event.stopPropagation()}>
              <Checkbox
                aria-label={label}
                checked={row.getIsSelected()}
                onCheckedChange={(value) => row.toggleSelected(Boolean(value))}
              />
            </div>
          );
        },
        enableSorting: false,
        enableResizing: false,
        size: 52,
        minSize: 52,
        meta: {
          className: "w-12 text-center",
          headerClassName: "w-12 text-center",
        },
      },
      ...mappedColumns,
    ];
  }, [
    columns,
    defaultColumnMinSize,
    enableColumnResizing,
    enableRowSelection,
    onSortChange,
    rowLabel,
  ]);

  const table = useReactTable({
    data,
    columns: columnDefs,
    state: {
      sorting: toSortingState(activeSortState),
      pagination: controlledPagination
        ? { pageIndex: Math.max(page - 1, 0), pageSize }
        : internalPagination,
      rowSelection,
    },
    manualSorting: sortState !== undefined && Boolean(onSortChange),
    manualPagination,
    pageCount: manualPagination && totalItems != null && pageSize
      ? Math.max(Math.ceil(totalItems / pageSize), 1)
      : undefined,
    enableRowSelection,
    enableSortingRemoval: true,
    columnResizeMode: "onChange",
    getRowId: getRowId ? (row) => getRowId(row) : undefined,
    onRowSelectionChange: setRowSelection,
    onPaginationChange: controlledPagination ? undefined : setInternalPagination,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: internalPaginationEnabled ? getPaginationRowModel() : undefined,
  });

  const visibleRows = table.getRowModel().rows;
  const selectedRows = table.getSelectedRowModel().rows.map((row) => row.original);
  const selectedCount = selectedRows.length;

  const effectivePage = controlledPagination ? page : table.getState().pagination.pageIndex + 1;
  const effectivePageSize = controlledPagination ? pageSize : table.getState().pagination.pageSize;
  const effectiveTotalItems = totalItems ?? data.length;
  const totalPages = controlledPagination
    ? Math.max(Math.ceil(effectiveTotalItems / effectivePageSize), 1)
    : internalPaginationEnabled
      ? Math.max(table.getPageCount(), 1)
      : 1;
  const pageStart = effectiveTotalItems > 0 ? (effectivePage - 1) * effectivePageSize + 1 : 0;
  const pageEnd = effectiveTotalItems > 0 ? Math.min(effectivePage * effectivePageSize, effectiveTotalItems) : 0;
  const canPreviousPage = controlledPagination ? effectivePage > 1 : table.getCanPreviousPage();
  const canNextPage = controlledPagination
    ? effectivePage < totalPages
    : internalPaginationEnabled
      ? table.getCanNextPage()
      : false;
  const showPagination = controlledPagination || internalPaginationEnabled;

  const handleSort = (columnId: string) => {
    const nextSortState = getNextSortState(activeSortState, columnId);

    if (onSortChange) {
      onSortChange(nextSortState);
      return;
    }

    setInternalSortState(nextSortState);
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
    <div className="min-w-0 space-y-4">
      {toolbar}

      {filterBar ?? null}

      {summary ? <div className="text-sm text-muted-foreground">{summary}</div> : null}

      {enableRowSelection && selectedCount > 0 ? (
        <div className="flex flex-col gap-3 rounded-2xl border border-primary/20 bg-primary/5 px-4 py-3 text-sm text-foreground sm:flex-row sm:items-center sm:justify-between">
          <span className="font-medium">{selectedCount.toLocaleString()} selected</span>
          <div className="flex flex-wrap items-center gap-2">
            {renderBulkActions?.({
              selectedRows,
              clearSelection: () => setRowSelection({}),
            })}
            <Button type="button" variant="ghost" size="sm" onClick={() => setRowSelection({})}>
              Clear selection
            </Button>
          </div>
        </div>
      ) : null}

      {error ? (
        <div role="alert" className="rounded-xl border border-destructive/20 bg-destructive/8 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      <div className="min-w-0 overflow-x-auto rounded-2xl border border-border/80 bg-card/90 shadow-sm">
        <Table className={cn("min-w-0", tableClassName)}>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id} className="bg-muted/35 hover:bg-muted/35">
                {headerGroup.headers.map((header) => {
                  const isActiveSort = activeSortState?.columnId === header.column.id;
                  const canSort = header.column.getCanSort();
                  const headerMeta = header.column.columnDef.meta as { headerClassName?: string } | undefined;
                  const headerLabel = columns.find((column) => column.id === header.column.id)?.header;
                  const resizeLabel = headerLabel ? `Resize ${String(headerLabel)}` : `Resize column ${header.column.id}`;
                  const SortIcon = !isActiveSort ? ArrowUpDown : activeSortState?.direction === "asc" ? ArrowUp : ArrowDown;

                  return (
                    <TableHead
                      key={header.id}
                      className={cn(
                        stickyHeader && "sticky top-0 z-10 bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/85",
                        enableColumnResizing && header.column.getCanResize() && "relative",
                        headerMeta?.headerClassName,
                      )}
                      style={{
                        width: header.getSize(),
                        position: stickyHeader ? "sticky" : undefined,
                        top: stickyHeader ? 0 : undefined,
                      }}
                      aria-sort={isActiveSort ? (activeSortState?.direction === "asc" ? "ascending" : "descending") : undefined}
                    >
                      {header.isPlaceholder ? null : canSort ? (
                        <button
                          type="button"
                          className={cn(
                            "group flex h-auto w-full items-center justify-between gap-2 rounded-none border-0 bg-transparent px-0 py-0 text-left text-xs font-semibold uppercase tracking-[0.18em] shadow-none outline-none transition-colors hover:bg-transparent focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-0",
                            isActiveSort
                              ? "text-foreground"
                              : "text-muted-foreground hover:text-foreground",
                          )}
                          onClick={() => handleSort(header.column.id)}
                        >
                          <span className="truncate">{flexRender(header.column.columnDef.header, header.getContext())}</span>
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
                        flexRender(header.column.columnDef.header, header.getContext())
                      )}

                      {enableColumnResizing && header.column.getCanResize() ? (
                        <div
                          role="separator"
                          aria-label={resizeLabel}
                          className={cn(
                            "absolute inset-y-0 right-0 w-2 cursor-col-resize touch-none select-none",
                            header.column.getIsResizing() && "bg-primary/30",
                          )}
                          onClick={(event) => event.stopPropagation()}
                          onDoubleClick={() => header.column.resetSize()}
                          onMouseDown={header.getResizeHandler()}
                          onTouchStart={header.getResizeHandler()}
                        />
                      ) : null}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {loading
              ? Array.from({ length: loadingRowCount }, (_, index) => (
                  <TableRow key={`loading-${index}`}>
                    {columnDefs.map((column, columnIndex) => (
                      <TableCell
                        key={`${column.id ?? columnIndex}-${index}`}
                        className={(column.meta as { className?: string } | undefined)?.className}
                      >
                        <Skeleton className="h-5 w-full" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              : visibleRows.length === 0
                ? (
                    <TableRow className="hover:bg-transparent">
                      <TableCell colSpan={columnDefs.length} className="px-6 py-10 text-center">
                        <div className="space-y-1.5">
                          <p className="text-sm font-medium text-foreground">{emptyTitle}</p>
                          <p className="text-sm text-muted-foreground">{emptyDescription}</p>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                : visibleRows.map((row) => (
                    <TableRow
                      key={row.id}
                      data-state={row.getIsSelected() ? "selected" : undefined}
                      className={cn(
                        onRowClick && "cursor-pointer focus-visible:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring/40",
                        getRowClassName?.(row.original),
                      )}
                      role={onRowClick ? "button" : undefined}
                      tabIndex={onRowClick ? 0 : undefined}
                      aria-label={onRowClick ? rowLabel?.(row.original) : undefined}
                      onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                      onKeyDown={(event) => handleRowKeyDown(event, row.original)}
                    >
                      {row.getVisibleCells().map((cell) => {
                        const cellMeta = cell.column.columnDef.meta as { className?: string } | undefined;
                        return (
                          <TableCell
                            key={cell.id}
                            className={cellMeta?.className}
                            style={{ width: cell.column.getSize() }}
                          >
                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  ))}
          </TableBody>
        </Table>
      </div>

      {showPagination ? (
        <div className="flex flex-col gap-3 border-t border-border/70 pt-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span aria-live="polite" className="tabular-nums">
            Showing {pageStart.toLocaleString()}-{pageEnd.toLocaleString()} of {effectiveTotalItems.toLocaleString()}
            <span className="hidden sm:inline"> · Page {effectivePage.toLocaleString()} of {totalPages.toLocaleString()}</span>
          </span>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              aria-label={`Go to previous page${effectivePage > 1 ? `, page ${(effectivePage - 1).toLocaleString()}` : ""}`}
              disabled={!canPreviousPage || loading}
              onClick={() => {
                if (controlledPagination) {
                  onPageChange?.(effectivePage - 1);
                  return;
                }

                table.previousPage();
              }}
            >
              Previous
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              aria-label={`Go to next page${effectivePage < totalPages ? `, page ${(effectivePage + 1).toLocaleString()}` : ""}`}
              disabled={!canNextPage || loading}
              onClick={() => {
                if (controlledPagination) {
                  onPageChange?.(effectivePage + 1);
                  return;
                }

                table.nextPage();
              }}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}