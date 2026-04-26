import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { DataTable, type DataTableSortState } from "../components/layout/DataTable";
import { PageHeader, SectionCard, SurfaceMessage } from "../components/layout/PageLayout";
import { Badge } from "../components/ui/badge";
import { buttonVariants, Button } from "../components/ui/button";
import { DatePicker } from "../components/ui/DatePicker";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  parseDatePickerInputValue,
  serializeDatePickerValue,
} from "../components/ui/date-picker-utils";
import { appTodayISO } from "../lib/time";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "../components/ui/sheet";
import { cn } from "../lib/utils";
import { SETTINGS_ROUTE } from "../lib/routes";
import {
  ADMIN_USER_ROLES,
  ADMIN_USER_STATUSES,
  backfillSalesMonthly,
  createUser,
  fetchAuditLogs,
  fetchLegacyRefreshLanes,
  fetchLegacyRefreshRecentRuns,
  fetchSalesMonthlyHealth,
  fetchUsers,
  repairSalesMonthlyMissing,
  type SalesMonthlyBackfillResponse,
  type SalesMonthlyHealthStatus,
  triggerLegacyRefresh,
  type AdminUser,
  type AdminUserCreateRequest,
  type AdminUserRole,
  type AdminUserStatus,
  type AdminUserUpdateRequest,
  type AuditLogEntry,
  type BatchPointer,
  type LegacyRefreshConflict,
  type LegacyRefreshJobLaunched,
  type LegacyRefreshLaneStatus,
  type RefreshJobRecord,
  type RefreshMode,
  updateUser,
} from "../lib/api/admin";
import {
  ROLE_PERMISSIONS,
  type AppFeature,
  type PermissionLevel,
} from "../hooks/usePermissions";

type UserDialogState =
  | { mode: "create" }
  | { mode: "edit"; user: AdminUser };

interface AdminUserFormState {
  email: string;
  display_name: string;
  role: AdminUserRole;
  status: AdminUserStatus;
  password: string;
}

type MatrixRole = "admin" | "owner" | AdminUserRole;
type PermissionLevelOrNone = PermissionLevel | "none";

interface AuditFilterState {
  actorId: string;
  actorType: string;
  action: string;
  entityType: string;
  entityId: string;
  createdAfter: string;
  createdBefore: string;
}

interface SavedAuditPreset {
  name: string;
  filters: AuditFilterState;
}

interface PermissionMatrixRow {
  feature: AppFeature;
  levels: Record<MatrixRole, PermissionLevelOrNone>;
}

const EMPTY_FORM: AdminUserFormState = {
  email: "",
  display_name: "",
  role: "sales",
  status: "active",
  password: "",
};

const EMPTY_AUDIT_FILTERS: AuditFilterState = {
  actorId: "",
  actorType: "",
  action: "",
  entityType: "",
  entityId: "",
  createdAfter: "",
  createdBefore: "",
};

const AUDIT_PRESET_STORAGE_KEY = "ultrerp_admin_audit_presets";
const AUDIT_PAGE_SIZE = 20;
const MATRIX_ROLES: MatrixRole[] = ["admin", "owner", "finance", "warehouse", "sales"];
const DEFAULT_AUDIT_SORT_STATE: DataTableSortState = {
  columnId: "created_at",
  direction: "desc",
};
const AUDIT_ACTION_SUGGESTIONS = [
  "user.create",
  "user.update",
  "approval.approve",
  "approval.reject",
  "inventory.adjust",
  "product.update",
];
const AUDIT_ACTOR_TYPE_SUGGESTIONS = ["user", "system"];
const AUDIT_ENTITY_SUGGESTIONS = [
  "user",
  "approval",
  "inventory_stock",
  "product",
  "settings",
];

function buildAuditFilterOptions(baseOptions: readonly string[], currentValue: string): string[] {
  const normalizedValue = currentValue.trim();
  if (!normalizedValue || baseOptions.includes(normalizedValue)) {
    return [...baseOptions];
  }
  return [normalizedValue, ...baseOptions];
}

function formatDateInput(date: Date): string {
  return serializeDatePickerValue(date);
}

function shiftCalendarDays(date: Date, days: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function formatAuditState(value: Record<string, unknown> | null): string | null {
  if (value == null) {
    return null;
  }
  return JSON.stringify(value, null, 2);
}

function cloneAuditFilters(filters: AuditFilterState): AuditFilterState {
  return { ...filters };
}

function loadSavedAuditPresets(): SavedAuditPreset[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(AUDIT_PRESET_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as Array<{ name?: unknown; filters?: Partial<AuditFilterState> }>;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed
      .filter((preset) => typeof preset.name === "string" && preset.name.trim())
      .map((preset) => ({
        name: String(preset.name).trim(),
        filters: {
          actorId: String(preset.filters?.actorId ?? ""),
          actorType: String(preset.filters?.actorType ?? ""),
          action: String(preset.filters?.action ?? ""),
          entityType: String(preset.filters?.entityType ?? ""),
          entityId: String(preset.filters?.entityId ?? ""),
          createdAfter: String(preset.filters?.createdAfter ?? ""),
          createdBefore: String(preset.filters?.createdBefore ?? ""),
        },
      }));
  } catch {
    return [];
  }
}

function persistSavedAuditPresets(presets: SavedAuditPreset[]) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(AUDIT_PRESET_STORAGE_KEY, JSON.stringify(presets));
}

function downloadTextFile(filename: string, content: string, mimeType: string, prependBom = false) {
  const blob = new Blob([prependBom ? `\uFEFF${content}` : content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function csvCell(value: unknown): string {
  return `"${String(value ?? "").replace(/"/g, '""')}"`;
}

function buildEditForm(user: AdminUser): AdminUserFormState {
  return {
    email: user.email,
    display_name: user.display_name,
    role: user.role,
    status: user.status,
    password: "",
  };
}

function statusVariant(status: AdminUserStatus) {
  switch (status) {
    case "active":
      return "success" as const;
    case "disabled":
      return "destructive" as const;
    default:
      return "outline" as const;
  }
}

function permissionVariant(level: PermissionLevelOrNone) {
  switch (level) {
    case "write":
      return "success" as const;
    case "read":
      return "info" as const;
    default:
      return "secondary" as const;
  }
}

function generateTemporaryPassword(length = 16): string {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*";
  const values = new Uint32Array(length);
  if (globalThis.crypto?.getRandomValues) {
    globalThis.crypto.getRandomValues(values);
  } else {
    for (let index = 0; index < length; index += 1) {
      values[index] = Math.floor(Math.random() * alphabet.length);
    }
  }
  return Array.from(values, (value) => alphabet[value % alphabet.length]).join("");
}

function toAuditDateBoundary(value: string, boundary: "start" | "end"): string | undefined {
  const trimmedValue = value.trim();
  if (!trimmedValue) {
    return undefined;
  }
  return boundary === "start"
    ? `${trimmedValue}T00:00:00`
    : `${trimmedValue}T23:59:59.999999`;
}

function validateForm(
  dialogState: UserDialogState | null,
  form: AdminUserFormState,
  t: (key: string) => string,
): string | null {
  if (!dialogState) {
    return t("adminPage.users.errors.formUnavailable");
  }
  if (dialogState.mode === "create") {
    if (!form.email.trim()) {
      return t("adminPage.users.errors.emailRequired");
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      return t("adminPage.users.errors.emailInvalid");
    }
  }
  if (!form.display_name.trim()) {
    return t("adminPage.users.errors.displayNameRequired");
  }
  if (dialogState.mode === "create" && form.password.trim().length < 8) {
    return t("adminPage.users.errors.passwordTooShort");
  }
  if (dialogState.mode === "edit" && form.password.trim() && form.password.trim().length < 8) {
    return t("adminPage.users.errors.resetPasswordTooShort");
  }
  return null;
}

export function AdminPage() {
  const { t } = useTranslation("common");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [usersLoading, setUsersLoading] = useState(true);
  const [auditLoading, setAuditLoading] = useState(true);
  const [usersError, setUsersError] = useState<string | null>(null);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [dialogState, setDialogState] = useState<UserDialogState | null>(null);
  const [formState, setFormState] = useState<AdminUserFormState>(EMPTY_FORM);
  const [dialogError, setDialogError] = useState<string | null>(null);
  const [dialogNotice, setDialogNotice] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<"all" | AdminUserRole>("all");
  const [statusFilter, setStatusFilter] = useState<"all" | AdminUserStatus>("all");
  const [auditFilters, setAuditFilters] = useState<AuditFilterState>(EMPTY_AUDIT_FILTERS);
  const [auditPage, setAuditPage] = useState(1);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditSortState, setAuditSortState] = useState<DataTableSortState | null>(DEFAULT_AUDIT_SORT_STATE);
  const [selectedAuditLog, setSelectedAuditLog] = useState<AuditLogEntry | null>(null);
  const [savedAuditPresetName, setSavedAuditPresetName] = useState("");
  const [savedAuditPresets, setSavedAuditPresets] = useState<SavedAuditPreset[]>(() => loadSavedAuditPresets());

  const auditActorTypeOptions = useMemo(
    () => buildAuditFilterOptions(AUDIT_ACTOR_TYPE_SUGGESTIONS, auditFilters.actorType),
    [auditFilters.actorType],
  );
  const auditActionOptions = useMemo(
    () => buildAuditFilterOptions(AUDIT_ACTION_SUGGESTIONS, auditFilters.action),
    [auditFilters.action],
  );
  const auditEntityOptions = useMemo(
    () => buildAuditFilterOptions(AUDIT_ENTITY_SUGGESTIONS, auditFilters.entityType),
    [auditFilters.entityType],
  );

  const roleLabel = (role: MatrixRole) => {
    if (role === "admin") {
      return t("routes.admin.label");
    }
    return t(`adminPage.users.roles.${role}`);
  };
  const statusLabel = (status: AdminUserStatus) => t(`adminPage.users.statuses.${status}`);
  const permissionLabel = (level: PermissionLevelOrNone) => t(`adminPage.permissions.levels.${level}`);

  const normalizedQuery = searchQuery.trim().toLowerCase();
  const filteredUsers = users.filter((user) => {
    const matchesQuery = normalizedQuery === ""
      || user.email.toLowerCase().includes(normalizedQuery)
      || user.display_name.toLowerCase().includes(normalizedQuery);
    const matchesRole = roleFilter === "all" || user.role === roleFilter;
    const matchesStatus = statusFilter === "all" || user.status === statusFilter;
    return matchesQuery && matchesRole && matchesStatus;
  });

  const permissionRows = useMemo<PermissionMatrixRow[]>(() => {
    const features: AppFeature[] = [
      "dashboard",
      "inventory",
      "purchases",
      "customers",
      "invoices",
      "orders",
      "payments",
      "admin",
      "owner_dashboard",
      "settings",
    ];
    return features.map((feature) => ({
      feature,
      levels: Object.fromEntries(
        MATRIX_ROLES.map((role) => [role, ROLE_PERMISSIONS[role]?.[feature] ?? "none"]),
      ) as Record<MatrixRole, PermissionLevelOrNone>,
    }));
  }, []);

  const loadUsers = useCallback(async () => {
    setUsersLoading(true);
    setUsersError(null);
    try {
      const response = await fetchUsers();
      setUsers(Array.isArray(response) ? response : []);
    } catch (err) {
      setUsersError(err instanceof Error ? err.message : t("adminPage.errors.loadFailed"));
    } finally {
      setUsersLoading(false);
    }
  }, [t]);

  const loadAuditLogs = useCallback(async () => {
    setAuditLoading(true);
    setAuditError(null);
    try {
      const response = await fetchAuditLogs({
        page: auditPage,
        page_size: AUDIT_PAGE_SIZE,
        action: auditFilters.action || undefined,
        actor_id: auditFilters.actorId || undefined,
        actor_type: auditFilters.actorType || undefined,
        entity_type: auditFilters.entityType || undefined,
        entity_id: auditFilters.entityId || undefined,
        created_after: toAuditDateBoundary(auditFilters.createdAfter, "start"),
        created_before: toAuditDateBoundary(auditFilters.createdBefore, "end"),
        sort_by: auditSortState?.columnId as "created_at" | "actor_id" | "actor_type" | "action" | "entity_id" | undefined,
        sort_direction: auditSortState?.direction,
      });
      const items = Array.isArray(response) ? response : response.items ?? [];
      const total = Array.isArray(response) ? items.length : response.total ?? items.length;
      setAuditLogs(items);
      setAuditTotal(total);
    } catch (err) {
      setAuditError(err instanceof Error ? err.message : t("adminPage.errors.loadFailed"));
    } finally {
      setAuditLoading(false);
    }
  }, [
    auditFilters.action,
    auditFilters.actorId,
    auditFilters.actorType,
    auditFilters.createdAfter,
    auditFilters.createdBefore,
    auditFilters.entityId,
    auditFilters.entityType,
    auditPage,
    auditSortState?.columnId,
    auditSortState?.direction,
    t,
  ]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  useEffect(() => {
    void loadAuditLogs();
  }, [loadAuditLogs]);

  function resetDialog() {
    setDialogState(null);
    setFormState(EMPTY_FORM);
    setDialogError(null);
    setDialogNotice(null);
  }

  function openCreateDialog() {
    setDialogState({ mode: "create" });
    setFormState(EMPTY_FORM);
    setDialogError(null);
    setDialogNotice(null);
  }

  function openEditDialog(user: AdminUser) {
    setDialogState({ mode: "edit", user });
    setFormState(buildEditForm(user));
    setDialogError(null);
    setDialogNotice(null);
  }

  function updateAuditFilter<K extends keyof AuditFilterState>(key: K, value: AuditFilterState[K]) {
    setAuditPage(1);
    setAuditFilters((current) => ({ ...current, [key]: value }));
  }

  function setAuditDateRange(createdAfter: string, createdBefore: string) {
    setAuditPage(1);
    setAuditFilters((current) => ({ ...current, createdAfter, createdBefore }));
  }

  function applyAuditDatePreset(preset: "today" | "last7Days" | "thisMonth") {
    const todayValue = appTodayISO();
    const today = parseDatePickerInputValue(todayValue) ?? new Date();

    if (preset === "today") {
      setAuditDateRange(todayValue, todayValue);
      return;
    }

    if (preset === "last7Days") {
      setAuditDateRange(formatDateInput(shiftCalendarDays(today, -6)), todayValue);
      return;
    }

    setAuditDateRange(`${todayValue.slice(0, 8)}01`, todayValue);
  }

  function clearAuditDateRange() {
    setAuditDateRange("", "");
  }

  function saveCurrentAuditPreset() {
    const name = savedAuditPresetName.trim();
    if (!name) {
      return;
    }
    const next = [
      { name, filters: cloneAuditFilters(auditFilters) },
      ...savedAuditPresets.filter((preset) => preset.name !== name),
    ].slice(0, 8);
    setSavedAuditPresets(next);
    persistSavedAuditPresets(next);
    setSavedAuditPresetName("");
  }

  function applySavedAuditPreset(preset: SavedAuditPreset) {
    setAuditPage(1);
    setAuditFilters(cloneAuditFilters(preset.filters));
  }

  function deleteSavedAuditPreset(name: string) {
    const next = savedAuditPresets.filter((preset) => preset.name !== name);
    setSavedAuditPresets(next);
    persistSavedAuditPresets(next);
  }

  function handleAuditSortChange(nextSortState: DataTableSortState | null) {
    setAuditPage(1);
    setAuditSortState(nextSortState);
  }

  function exportAuditLogs(format: "csv" | "json") {
    if (auditLogs.length === 0) {
      return;
    }

    const filenameBase = `audit-log-${formatDateInput(new Date())}`;
    if (format === "json") {
      downloadTextFile(
        `${filenameBase}.json`,
        JSON.stringify(auditLogs, null, 2),
        "application/json;charset=utf-8;",
      );
      return;
    }

    const rows = auditLogs.map((entry) => [
      entry.created_at,
      entry.actor_id,
      entry.actor_type,
      entry.action,
      entry.entity_type,
      entry.entity_id,
      entry.correlation_id ?? "",
      entry.notes ?? "",
      JSON.stringify(entry.before_state ?? null),
      JSON.stringify(entry.after_state ?? null),
    ]);
    const csv = [
      [
        "created_at",
        "actor_id",
        "actor_type",
        "action",
        "entity_type",
        "entity_id",
        "correlation_id",
        "notes",
        "before_state",
        "after_state",
      ],
      ...rows,
    ]
      .map((row) => row.map(csvCell).join(","))
      .join("\n");

    downloadTextFile(`${filenameBase}.csv`, csv, "text/csv;charset=utf-8;", true);
  }

  function handleGeneratePassword() {
    const nextPassword = generateTemporaryPassword();
    setFormState((current) => ({ ...current, password: nextPassword }));
    setDialogNotice(t("adminPage.users.dialog.passwordGenerated"));
    setDialogError(null);
  }

  async function handleCopyPassword() {
    if (!formState.password.trim()) {
      return;
    }
    try {
      await navigator.clipboard.writeText(formState.password);
      setDialogNotice(t("adminPage.users.dialog.passwordCopied"));
    } catch {
      setDialogError(t("adminPage.users.errors.copyFailed"));
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationError = validateForm(dialogState, formState, t);
    if (validationError) {
      setDialogError(validationError);
      return;
    }
    if (!dialogState) {
      return;
    }

    setSubmitting(true);
    setDialogError(null);
    setDialogNotice(null);
    try {
      if (dialogState.mode === "create") {
        const payload: AdminUserCreateRequest = {
          email: formState.email.trim().toLowerCase(),
          display_name: formState.display_name.trim(),
          role: formState.role,
          password: formState.password.trim(),
        };
        await createUser(payload);
      } else {
        const payload: AdminUserUpdateRequest = {
          display_name: formState.display_name.trim(),
          role: formState.role,
          status: formState.status,
        };
        if (formState.password.trim()) {
          payload.password = formState.password.trim();
        }
        await updateUser(dialogState.user.id, payload);
      }
      await Promise.all([loadUsers(), loadAuditLogs()]);
      resetDialog();
    } catch (err) {
      setDialogError(err instanceof Error ? err.message : t("adminPage.errors.saveFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="space-y-6">
        <PageHeader
          eyebrow={t("adminPage.eyebrow")}
          title={t("adminPage.title")}
          description={t("adminPage.description")}
        />

        {usersError ? <SurfaceMessage tone="danger">{usersError}</SurfaceMessage> : null}
        {auditError ? <SurfaceMessage tone="danger">{auditError}</SurfaceMessage> : null}

        <div className="grid gap-4 lg:grid-cols-2">
          <SectionCard
            title={t("adminPage.users.title")}
            description={t("adminPage.users.description")}
            actions={(
              <Button onClick={openCreateDialog}>{t("adminPage.users.addUser")}</Button>
            )}
          >
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
              <div className="min-w-0 flex-1 space-y-2">
                <Label htmlFor="admin-user-search">{t("adminPage.users.filters.search")}</Label>
                <Input
                  id="admin-user-search"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder={t("adminPage.users.filters.searchPlaceholder")}
                />
              </div>
              <div className="space-y-2 sm:w-44">
                <Label htmlFor="admin-role-filter">{t("adminPage.users.filters.role")}</Label>
                <select
                  id="admin-role-filter"
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  value={roleFilter}
                  onChange={(event) => setRoleFilter(event.target.value as "all" | AdminUserRole)}
                >
                  <option value="all">{t("adminPage.users.filters.allRoles")}</option>
                  {ADMIN_USER_ROLES.map((role) => (
                    <option key={role} value={role}>
                      {roleLabel(role)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2 sm:w-44">
                <Label htmlFor="admin-status-filter">{t("adminPage.users.filters.status")}</Label>
                <select
                  id="admin-status-filter"
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  value={statusFilter}
                  onChange={(event) =>
                    setStatusFilter(event.target.value as "all" | AdminUserStatus)
                  }
                >
                  <option value="all">{t("adminPage.users.filters.allStatuses")}</option>
                  {ADMIN_USER_STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {statusLabel(status)}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <DataTable
              columns={[
                {
                  id: "email",
                  header: t("adminPage.users.columns.email"),
                  sortable: true,
                  getSortValue: (user) => user.email,
                  cell: (user) => <span className="font-medium">{user.email}</span>,
                },
                {
                  id: "display_name",
                  header: t("adminPage.users.columns.displayName"),
                  sortable: true,
                  getSortValue: (user) => user.display_name,
                  cell: (user) => user.display_name,
                },
                {
                  id: "role",
                  header: t("adminPage.users.columns.role"),
                  sortable: true,
                  getSortValue: (user) => user.role,
                  cell: (user) => roleLabel(user.role),
                },
                {
                  id: "status",
                  header: t("adminPage.users.columns.status"),
                  sortable: true,
                  getSortValue: (user) => user.status,
                  cell: (user) => (
                    <Badge variant={statusVariant(user.status)} className="normal-case tracking-normal">
                      {statusLabel(user.status)}
                    </Badge>
                  ),
                },
                {
                  id: "actions",
                  header: t("adminPage.users.columns.actions"),
                  cell: (user) => (
                    <Button variant="outline" size="sm" onClick={() => openEditDialog(user)}>
                      {t("adminPage.users.editUser")}
                    </Button>
                  ),
                },
              ]}
              data={filteredUsers}
              summary={t("adminPage.users.summary", {
                filtered: filteredUsers.length,
                total: users.length,
              })}
              loading={usersLoading && users.length === 0}
              emptyTitle={t("adminPage.users.emptyTitle")}
              emptyDescription={t("adminPage.users.emptyDescription")}
              getRowId={(user) => user.id}
            />
          </SectionCard>

          <SectionCard
            title={t("adminPage.auditLog.title")}
            description={t("adminPage.auditLog.description")}
            actions={(
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => exportAuditLogs("csv")}
                  disabled={auditLogs.length === 0}
                >
                  {t("adminPage.auditLog.export.csv")}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => exportAuditLogs("json")}
                  disabled={auditLogs.length === 0}
                >
                  {t("adminPage.auditLog.export.json")}
                </Button>
              </div>
            )}
          >
            <div className="mb-4 rounded-2xl border border-border/70 bg-muted/15 p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-end">
                <div className="min-w-0 flex-1 space-y-2">
                  <Label htmlFor="admin-audit-preset-name">{t("adminPage.auditLog.savedPresets.name")}</Label>
                  <Input
                    id="admin-audit-preset-name"
                    value={savedAuditPresetName}
                    onChange={(event) => setSavedAuditPresetName(event.target.value)}
                    placeholder={t("adminPage.auditLog.savedPresets.namePlaceholder")}
                  />
                </div>
                <Button
                  variant="outline"
                  onClick={saveCurrentAuditPreset}
                  disabled={!savedAuditPresetName.trim()}
                >
                  {t("adminPage.auditLog.savedPresets.save")}
                </Button>
              </div>

              {savedAuditPresets.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">
                  {t("adminPage.auditLog.savedPresets.empty")}
                </p>
              ) : (
                <div className="mt-3 flex flex-wrap gap-2">
                  {savedAuditPresets.map((preset) => (
                    <div
                      key={preset.name}
                      className="flex items-center gap-1 rounded-full border border-border/70 bg-background px-2 py-1"
                    >
                      <Button variant="ghost" size="sm" onClick={() => applySavedAuditPreset(preset)}>
                        {preset.name}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        aria-label={t("adminPage.auditLog.savedPresets.delete")}
                        onClick={() => deleteSavedAuditPreset(preset.name)}
                      >
                        {t("adminPage.auditLog.savedPresets.delete")}
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="mb-4 flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={() => applyAuditDatePreset("today")}>
                {t("adminPage.auditLog.presets.today")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => applyAuditDatePreset("last7Days")}>
                {t("adminPage.auditLog.presets.last7Days")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => applyAuditDatePreset("thisMonth")}>
                {t("adminPage.auditLog.presets.thisMonth")}
              </Button>
              <Button variant="ghost" size="sm" onClick={clearAuditDateRange}>
                {t("adminPage.auditLog.presets.clear")}
              </Button>
            </div>

            <div className="mb-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="space-y-2">
                <Label htmlFor="admin-audit-actor">{t("adminPage.auditLog.filters.actor")}</Label>
                <Input
                  id="admin-audit-actor"
                  value={auditFilters.actorId}
                  onChange={(event) => updateAuditFilter("actorId", event.target.value)}
                  placeholder={t("adminPage.auditLog.filters.actorPlaceholder")}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="admin-audit-actor-type">{t("adminPage.auditLog.filters.actorType")}</Label>
                <select
                  id="admin-audit-actor-type"
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  value={auditFilters.actorType}
                  onChange={(event) => updateAuditFilter("actorType", event.target.value)}
                >
                  <option value="">{t("adminPage.auditLog.filters.actorTypePlaceholder")}</option>
                  {auditActorTypeOptions.map((actorType) => (
                    <option key={actorType} value={actorType}>
                      {actorType}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="admin-audit-action">{t("adminPage.auditLog.filters.action")}</Label>
                <select
                  id="admin-audit-action"
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  value={auditFilters.action}
                  onChange={(event) => updateAuditFilter("action", event.target.value)}
                >
                  <option value="">{t("adminPage.auditLog.filters.actionPlaceholder")}</option>
                  {auditActionOptions.map((action) => (
                    <option key={action} value={action}>
                      {action}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="admin-audit-entity-type">{t("adminPage.auditLog.filters.entityType")}</Label>
                <select
                  id="admin-audit-entity-type"
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  value={auditFilters.entityType}
                  onChange={(event) => updateAuditFilter("entityType", event.target.value)}
                >
                  <option value="">{t("adminPage.auditLog.filters.entityTypePlaceholder")}</option>
                  {auditEntityOptions.map((entityType) => (
                    <option key={entityType} value={entityType}>
                      {entityType}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="admin-audit-entity-id">{t("adminPage.auditLog.filters.entityId")}</Label>
                <Input
                  id="admin-audit-entity-id"
                  value={auditFilters.entityId}
                  onChange={(event) => updateAuditFilter("entityId", event.target.value)}
                  placeholder={t("adminPage.auditLog.filters.entityIdPlaceholder")}
                />
              </div>
              <div className="space-y-2">
                <Label>
                  {t("adminPage.auditLog.filters.createdAfter")} / {t("adminPage.auditLog.filters.createdBefore")}
                </Label>
                <div className="grid gap-2 sm:grid-cols-2">
                  <div className="space-y-1">
                    <span
                      id="admin-audit-created-after-label"
                      className="text-xs text-muted-foreground"
                    >
                      {t("adminPage.auditLog.filters.createdAfter")}
                    </span>
                    <DatePicker
                      id="admin-audit-created-after"
                      aria-labelledby="admin-audit-created-after-label"
                      placeholder={t("adminPage.auditLog.filters.createdAfter")}
                      value={parseDatePickerInputValue(auditFilters.createdAfter)}
                      onChange={(value) =>
                        setAuditDateRange(
                          serializeDatePickerValue(value),
                          auditFilters.createdBefore,
                        )
                      }
                      className="w-full"
                    />
                  </div>
                  <div className="space-y-1">
                    <span
                      id="admin-audit-created-before-label"
                      className="text-xs text-muted-foreground"
                    >
                      {t("adminPage.auditLog.filters.createdBefore")}
                    </span>
                    <DatePicker
                      id="admin-audit-created-before"
                      aria-labelledby="admin-audit-created-before-label"
                      placeholder={t("adminPage.auditLog.filters.createdBefore")}
                      value={parseDatePickerInputValue(auditFilters.createdBefore)}
                      onChange={(value) =>
                        setAuditDateRange(
                          auditFilters.createdAfter,
                          serializeDatePickerValue(value),
                        )
                      }
                      className="w-full"
                    />
                  </div>
                </div>
              </div>
            </div>

            <DataTable
              columns={[
                {
                  id: "created_at",
                  header: t("adminPage.auditLog.columns.createdAt"),
                  getSortValue: (entry) => new Date(entry.created_at).getTime(),
                  cell: (entry) => new Date(entry.created_at).toLocaleString(),
                },
                {
                  id: "actor_id",
                  header: t("adminPage.auditLog.columns.actor"),
                  getSortValue: (entry) => entry.actor_id,
                  cell: (entry) => entry.actor_id,
                },
                {
                  id: "actor_type",
                  header: t("adminPage.auditLog.columns.actorType"),
                  getSortValue: (entry) => entry.actor_type,
                  cell: (entry) => entry.actor_type,
                },
                {
                  id: "action",
                  header: t("adminPage.auditLog.columns.action"),
                  getSortValue: (entry) => entry.action,
                  cell: (entry) => entry.action,
                },
                {
                  id: "entity_id",
                  header: t("adminPage.auditLog.columns.target"),
                  getSortValue: (entry) => `${entry.entity_type}:${entry.entity_id}`,
                  cell: (entry) => `${entry.entity_type}:${entry.entity_id}`,
                },
                {
                  id: "details",
                  header: t("adminPage.auditLog.columns.details"),
                  cell: (entry) => (
                    <Button variant="ghost" size="sm" onClick={() => setSelectedAuditLog(entry)}>
                      {t("adminPage.auditLog.actions.view")}
                    </Button>
                  ),
                },
              ]}
              data={auditLogs}
              summary={t("adminPage.auditLog.summary", {
                filtered: auditLogs.length,
                total: auditTotal,
              })}
              loading={auditLoading && auditLogs.length === 0}
              emptyTitle={t("adminPage.auditLog.emptyTitle")}
              emptyDescription={t("adminPage.auditLog.emptyDescription")}
              page={auditPage}
              pageSize={AUDIT_PAGE_SIZE}
              totalItems={auditTotal}
              onPageChange={setAuditPage}
              sortState={auditSortState}
              onSortChange={handleAuditSortChange}
              getRowId={(entry) => entry.id}
            />
          </SectionCard>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <SectionCard
            title={t("adminPage.permissions.title")}
            description={t("adminPage.permissions.description")}
          >
            <DataTable
              columns={[
                {
                  id: "feature",
                  header: t("adminPage.permissions.columns.feature"),
                  cell: (row) => t(`adminPage.permissions.features.${row.feature}`),
                },
                ...MATRIX_ROLES.map((role) => ({
                  id: role,
                  header: roleLabel(role),
                  cell: (row: PermissionMatrixRow) => (
                    <Badge variant={permissionVariant(row.levels[role])} className="normal-case tracking-normal">
                      {permissionLabel(row.levels[role])}
                    </Badge>
                  ),
                })),
              ]}
              data={permissionRows}
              emptyTitle={t("adminPage.permissions.emptyTitle")}
              emptyDescription={t("adminPage.permissions.emptyDescription")}
              getRowId={(row) => row.feature}
            />
          </SectionCard>

          <SectionCard
            title={t("adminPage.settingsHub.title")}
            description={t("adminPage.settingsHub.description")}
            actions={(
              <Link className={cn(buttonVariants({ variant: "outline", size: "sm" }))} to={SETTINGS_ROUTE}>
                {t("adminPage.settingsHub.openSettings")}
              </Link>
            )}
          >
            <ul className="space-y-3 text-sm text-muted-foreground">
              <li>{t("adminPage.settingsHub.items.general")}</li>
              <li>{t("adminPage.settingsHub.items.security")}</li>
              <li>{t("adminPage.settingsHub.items.appearance")}</li>
              <li>{t("adminPage.settingsHub.items.data")}</li>
            </ul>
          </SectionCard>
        </div>

        {/* Legacy Refresh Control Plane (Story 15.28) */}
        <LegacyRefreshSection />
      </div>

      <Dialog
        open={dialogState !== null}
        onOpenChange={(open) => {
          if (!open && !submitting) {
            resetDialog();
          }
        }}
      >
        <DialogContent aria-describedby="admin-user-dialog-description">
          <DialogHeader>
            <DialogTitle>
              {dialogState?.mode === "edit"
                ? t("adminPage.users.dialog.editTitle")
                : t("adminPage.users.dialog.createTitle")}
            </DialogTitle>
            <DialogDescription id="admin-user-dialog-description">
              {dialogState?.mode === "edit"
                ? t("adminPage.users.dialog.editDescription")
                : t("adminPage.users.dialog.createDescription")}
            </DialogDescription>
          </DialogHeader>

          <form className="space-y-4" onSubmit={handleSubmit}>
            {dialogError ? <SurfaceMessage tone="danger">{dialogError}</SurfaceMessage> : null}
            {dialogNotice ? <SurfaceMessage tone="default">{dialogNotice}</SurfaceMessage> : null}

            <div className="space-y-2">
              <Label htmlFor="admin-user-email">{t("adminPage.users.fields.email")}</Label>
              <Input
                id="admin-user-email"
                type="email"
                value={formState.email}
                disabled={dialogState?.mode === "edit" || submitting}
                onChange={(event) => setFormState((current) => ({ ...current, email: event.target.value }))}
                required={dialogState?.mode === "create"}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="admin-user-display-name">
                {t("adminPage.users.fields.displayName")}
              </Label>
              <Input
                id="admin-user-display-name"
                value={formState.display_name}
                disabled={submitting}
                onChange={(event) =>
                  setFormState((current) => ({ ...current, display_name: event.target.value }))
                }
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="admin-user-role">{t("adminPage.users.fields.role")}</Label>
              <select
                id="admin-user-role"
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                value={formState.role}
                disabled={submitting}
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    role: event.target.value as AdminUserRole,
                  }))
                }
              >
                {ADMIN_USER_ROLES.map((role) => (
                  <option key={role} value={role}>
                    {roleLabel(role)}
                  </option>
                ))}
              </select>
            </div>

            {dialogState?.mode === "edit" ? (
              <div className="space-y-2">
                <Label htmlFor="admin-user-status">{t("adminPage.users.fields.status")}</Label>
                <select
                  id="admin-user-status"
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  value={formState.status}
                  disabled={submitting}
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      status: event.target.value as AdminUserStatus,
                    }))
                  }
                >
                  {ADMIN_USER_STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {statusLabel(status)}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}

            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <Label htmlFor="admin-user-password">
                  {dialogState?.mode === "edit"
                    ? t("adminPage.users.fields.resetPassword")
                    : t("adminPage.users.fields.password")}
                </Label>
                <div className="flex gap-2">
                  <Button type="button" variant="outline" size="sm" onClick={handleGeneratePassword}>
                    {t("adminPage.users.dialog.generatePassword")}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      void handleCopyPassword();
                    }}
                    disabled={!formState.password.trim()}
                  >
                    {t("adminPage.users.dialog.copyPassword")}
                  </Button>
                </div>
              </div>
              <Input
                id="admin-user-password"
                type="password"
                value={formState.password}
                disabled={submitting}
                onChange={(event) => setFormState((current) => ({ ...current, password: event.target.value }))}
                required={dialogState?.mode === "create"}
                minLength={8}
              />
              <p className="text-xs text-muted-foreground">
                {dialogState?.mode === "edit"
                  ? t("adminPage.users.dialog.resetPasswordHelp")
                  : t("adminPage.users.dialog.passwordHelp")}
              </p>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={resetDialog} disabled={submitting}>
                {t("adminPage.users.dialog.cancel")}
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting
                  ? dialogState?.mode === "edit"
                    ? t("adminPage.users.dialog.saving")
                    : t("adminPage.users.dialog.creating")
                  : dialogState?.mode === "edit"
                    ? t("adminPage.users.dialog.save")
                    : t("adminPage.users.dialog.createAction")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Sheet
        open={selectedAuditLog !== null}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedAuditLog(null);
          }
        }}
      >
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>{t("adminPage.auditLog.detailSheet.title")}</SheetTitle>
            <SheetDescription>{t("adminPage.auditLog.detailSheet.description")}</SheetDescription>
          </SheetHeader>

          {selectedAuditLog ? (
            <div className="mt-6 space-y-6 text-sm">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {t("adminPage.auditLog.detailSheet.fields.createdAt")}
                  </p>
                  <p>{new Date(selectedAuditLog.created_at).toLocaleString()}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {t("adminPage.auditLog.detailSheet.fields.action")}
                  </p>
                  <p>{selectedAuditLog.action}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {t("adminPage.auditLog.detailSheet.fields.actor")}
                  </p>
                  <p>{selectedAuditLog.actor_id}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {t("adminPage.auditLog.detailSheet.fields.actorType")}
                  </p>
                  <p>{selectedAuditLog.actor_type}</p>
                </div>
                <div className="space-y-1 sm:col-span-2">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {t("adminPage.auditLog.detailSheet.fields.target")}
                  </p>
                  <p>{`${selectedAuditLog.entity_type}:${selectedAuditLog.entity_id}`}</p>
                </div>
                <div className="space-y-1 sm:col-span-2">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {t("adminPage.auditLog.detailSheet.fields.correlationId")}
                  </p>
                  <p>{selectedAuditLog.correlation_id ?? t("adminPage.auditLog.detailSheet.emptyState")}</p>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                  {t("adminPage.auditLog.detailSheet.fields.notes")}
                </p>
                <div className="rounded-xl border border-border/70 bg-muted/20 px-4 py-3 text-sm">
                  {selectedAuditLog.notes ?? t("adminPage.auditLog.detailSheet.emptyState")}
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                  {t("adminPage.auditLog.detailSheet.fields.beforeState")}
                </p>
                <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-xl border border-border/70 bg-muted/20 p-4 text-xs leading-6 text-foreground">
                  {formatAuditState(selectedAuditLog.before_state) ?? t("adminPage.auditLog.detailSheet.emptyState")}
                </pre>
              </div>

              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                  {t("adminPage.auditLog.detailSheet.fields.afterState")}
                </p>
                <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-xl border border-border/70 bg-muted/20 p-4 text-xs leading-6 text-foreground">
                  {formatAuditState(selectedAuditLog.after_state) ?? t("adminPage.auditLog.detailSheet.emptyState")}
                </pre>
              </div>
            </div>
          ) : null}
        </SheetContent>
      </Sheet>
    </>
  );
}

// ---------------------------------------------------------------------------
// Legacy Refresh Control Plane (Story 15.28)
// ---------------------------------------------------------------------------

const LEGACY_REFRESH_POLL_INTERVAL_MS = 10_000;

interface LegacyRefreshTriggerFormState {
  tenantId: string;
  schemaName: string;
  sourceSchema: string;
  mode: RefreshMode;
  dryRun: boolean;
  lookbackDays: number;
  reconciliationThreshold: number;
}

const DEFAULT_REFRESH_FORM: LegacyRefreshTriggerFormState = {
  tenantId: "",
  schemaName: "",
  sourceSchema: "public",
  mode: "incremental",
  dryRun: false,
  lookbackDays: 0,
  reconciliationThreshold: 0,
};

interface SalesMonthlyOpsFormState {
  tenantId: string;
  startMonth: string;
  endMonth: string;
}

function startOfCalendarMonth(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), 1);
}

function shiftCalendarMonths(value: Date, months: number): Date {
  return new Date(value.getFullYear(), value.getMonth() + months, 1);
}

function buildDefaultSalesMonthlyOpsForm(): SalesMonthlyOpsFormState {
  const today = parseDatePickerInputValue(appTodayISO()) ?? new Date();
  const currentMonth = startOfCalendarMonth(today);
  const previousClosedMonth = shiftCalendarMonths(currentMonth, -1);
  return {
    tenantId: "",
    startMonth: serializeDatePickerValue(previousClosedMonth),
    endMonth: serializeDatePickerValue(previousClosedMonth),
  };
}

const DEFAULT_SALES_MONTHLY_FORM = buildDefaultSalesMonthlyOpsForm();

function formatDisposition(disp: string | null | undefined): string {
  if (!disp) return "unknown";
  return disp
    .replace(/-/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function dispositionVariant(disp: string | null | undefined): "success" | "warning" | "destructive" | "info" | "outline" {
  if (!disp) return "outline";
  const normalized = disp.toLowerCase();
  if (normalized.includes("completed") || normalized.includes("success") || normalized.includes("eligible")) return "success";
  if (normalized.includes("review") || normalized.includes("warning")) return "warning";
  if (normalized.includes("blocked") || normalized.includes("failed")) return "destructive";
  return "info";
}

function BatchPointerDisplay({ ptr, label }: { ptr: BatchPointer | null; label: string }) {
  if (!ptr) {
    return (
      <div className="space-y-1">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
        <p className="text-sm text-muted-foreground">—</p>
      </div>
    );
  }
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <div className="space-y-0.5 text-xs">
        <p className="font-mono">{ptr.batch_id ?? "—"}</p>
        {ptr.started_at && (
          <p className="text-muted-foreground">
            {new Date(ptr.started_at).toLocaleString()}
          </p>
        )}
        {ptr.final_disposition && (
          <Badge variant={dispositionVariant(ptr.final_disposition)} className="normal-case tracking-normal">
            {formatDisposition(ptr.final_disposition)}
          </Badge>
        )}
        {ptr.promotion_policy && (
          <p className="text-muted-foreground">
            Promotion: {String(ptr.promotion_policy.classification ?? "unknown")}
          </p>
        )}
      </div>
    </div>
  );
}

function LaneStatusCard({ status }: { status: LegacyRefreshLaneStatus }) {
  const { t } = useTranslation("common");
  const affectedDomainsLabel = status.affected_domains.length > 0
    ? status.affected_domains.join(", ")
    : t("adminPage.legacyRefresh.details.noAffectedDomains");

  return (
    <div className="rounded-2xl border border-border/70 bg-muted/10 p-4 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-mono text-sm font-medium">{status.lane_key}</p>
          <p className="text-xs text-muted-foreground">
            {status.schema_name} / {status.source_schema}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          {status.lane_locked ? (
            <Badge variant="warning" className="normal-case tracking-normal">
              {t("adminPage.legacyRefresh.status.locked")}
            </Badge>
          ) : (
            <Badge variant="success" className="normal-case tracking-normal">
              {t("adminPage.legacyRefresh.status.idle")}
            </Badge>
          )}
          {status.promotion_eligible && (
            <Badge variant="success" className="normal-case tracking-normal">
              {t("adminPage.legacyRefresh.status.eligible")}
            </Badge>
          )}
          {status.promotion_classification && !status.promotion_eligible && (
            <Badge variant="outline" className="normal-case tracking-normal">
              {String(status.promotion_classification)}
            </Badge>
          )}
        </div>
      </div>

      {status.blocked_reason && (
        <SurfaceMessage tone="danger" className="text-xs">
          {t("adminPage.legacyRefresh.status.blocked")}: {status.blocked_reason}
        </SurfaceMessage>
      )}

      {status.root_failure && (
        <SurfaceMessage tone="warning" className="text-xs">
          {status.root_failure}
        </SurfaceMessage>
      )}

      <div className="grid gap-3 rounded-xl border border-border/50 bg-background/70 p-3 text-xs sm:grid-cols-2">
        <div className="space-y-1">
          <p className="font-medium text-muted-foreground">
            {t("adminPage.legacyRefresh.details.currentMode")}
          </p>
          <p>{status.current_batch_mode ? formatDisposition(status.current_batch_mode) : "-"}</p>
        </div>
        <div className="space-y-1">
          <p className="font-medium text-muted-foreground">
            {t("adminPage.legacyRefresh.details.affectedDomains")}
          </p>
          <p>{affectedDomainsLabel}</p>
        </div>
        <div className="space-y-1 sm:col-span-2">
          <p className="font-medium text-muted-foreground">
            {t("adminPage.legacyRefresh.details.summaryPath")}
          </p>
          <p className="break-all font-mono text-[11px]">
            {status.latest_run?.summary_path ?? "-"}
          </p>
        </div>
        <div className="space-y-1 sm:col-span-2">
          <p className="font-medium text-muted-foreground">
            {t("adminPage.legacyRefresh.details.incrementalStatePath")}
          </p>
          <p className="break-all font-mono text-[11px]">
            {status.incremental_state_path ?? "-"}
          </p>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <BatchPointerDisplay
          ptr={status.latest_run}
          label={t("adminPage.legacyRefresh.columns.latestRun")}
        />
        <BatchPointerDisplay
          ptr={status.latest_success}
          label={t("adminPage.legacyRefresh.columns.latestSuccess")}
        />
        <BatchPointerDisplay
          ptr={status.latest_promoted}
          label={t("adminPage.legacyRefresh.columns.latestPromoted")}
        />
      </div>
    </div>
  );
}

function RecentRunsTable({ runs }: { runs: RefreshJobRecord[] }) {
  const { t } = useTranslation("common");
  if (runs.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        {t("adminPage.legacyRefresh.recentRuns.empty")}
      </p>
    );
  }
  return (
    <div className="space-y-2">
      {runs.slice(0, 10).map((run) => (
        <div
          key={run.job_id}
          className="flex items-center justify-between gap-3 rounded-xl border border-border/50 bg-muted/10 px-4 py-2 text-xs"
        >
          <div className="min-w-0 flex-1">
            <p className="truncate font-mono font-medium">{run.batch_id}</p>
            <p className="text-muted-foreground">
              {new Date(run.started_at).toLocaleString()}
              {run.completed_at && (
                <> → {new Date(run.completed_at).toLocaleString()}</>
              )}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <Badge variant={dispositionVariant(run.final_disposition)} className="normal-case tracking-normal">
              {formatDisposition(run.final_disposition)}
            </Badge>
            {run.blocked && (
              <Badge variant="warning" className="normal-case tracking-normal">
                {run.blocked_reason ?? "blocked"}
              </Badge>
            )}
            {run.promotion_eligible && (
              <Badge variant="success" className="normal-case tracking-normal">
                {t("adminPage.legacyRefresh.status.eligible")}
              </Badge>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function LegacyRefreshSection() {
  const { t } = useTranslation("common");
  const [lanes, setLanes] = useState<LegacyRefreshLaneStatus[]>([]);
  const [recentRuns, setRecentRuns] = useState<RefreshJobRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [triggerLoading, setTriggerLoading] = useState(false);
  const [triggerResult, setTriggerResult] = useState<LegacyRefreshJobLaunched | LegacyRefreshConflict | null>(null);
  const [triggerError, setTriggerError] = useState<string | null>(null);
  const [form, setForm] = useState<LegacyRefreshTriggerFormState>(DEFAULT_REFRESH_FORM);
  const [salesMonthlyForm, setSalesMonthlyForm] = useState<SalesMonthlyOpsFormState>(DEFAULT_SALES_MONTHLY_FORM);
  const [salesMonthlyHealth, setSalesMonthlyHealth] = useState<SalesMonthlyHealthStatus | null>(null);
  const [salesMonthlyError, setSalesMonthlyError] = useState<string | null>(null);
  const [salesMonthlyNotice, setSalesMonthlyNotice] = useState<string | null>(null);
  const [salesMonthlyLoading, setSalesMonthlyLoading] = useState(false);
  const [salesMonthlyAction, setSalesMonthlyAction] = useState<"repair" | "backfill" | null>(null);

  const loadLanes = useCallback(async () => {
    try {
      const result = await fetchLegacyRefreshLanes();
      setLanes(result.lanes);
    } catch (err) {
      console.error("Failed to load lanes:", err);
    }
  }, []);

  const loadRecentRuns = useCallback(async () => {
    try {
      const runs = await fetchLegacyRefreshRecentRuns(10);
      setRecentRuns(runs);
    } catch (err) {
      console.error("Failed to load recent runs:", err);
    }
  }, []);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([loadLanes(), loadRecentRuns()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("adminPage.errors.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [loadLanes, loadRecentRuns, t]);

  // Initial load + polling (AC4)
  useEffect(() => {
    void loadAll();
    const pollInterval = setInterval(() => {
      void loadLanes();
      void loadRecentRuns();
    }, LEGACY_REFRESH_POLL_INTERVAL_MS);
    return () => clearInterval(pollInterval);
  }, [loadAll, loadLanes, loadRecentRuns]);

  async function handleTrigger(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTriggerLoading(true);
    setTriggerError(null);
    setTriggerResult(null);

    try {
      const result = await triggerLegacyRefresh({
        tenant_id: form.tenantId,
        schema_name: form.schemaName,
        source_schema: form.sourceSchema,
        mode: form.mode,
        dry_run: form.dryRun,
        lookback_days: form.lookbackDays,
        reconciliation_threshold: form.reconciliationThreshold,
      });
      setTriggerResult(result);
      if ("conflict" in result) {
        setTriggerError(result.detail);
      } else {
        void loadAll();
      }
    } catch (err) {
      setTriggerError(err instanceof Error ? err.message : t("adminPage.errors.saveFailed"));
    } finally {
      setTriggerLoading(false);
    }
  }

  async function handleSalesMonthlyHealthCheck() {
    const tenantId = salesMonthlyForm.tenantId.trim();
    if (!tenantId) {
      return;
    }
    setSalesMonthlyLoading(true);
    setSalesMonthlyError(null);
    setSalesMonthlyNotice(null);
    try {
      const result = await fetchSalesMonthlyHealth(
        tenantId,
        salesMonthlyForm.startMonth || undefined,
        salesMonthlyForm.endMonth || undefined,
      );
      setSalesMonthlyHealth(result);
      setSalesMonthlyNotice(
        result.is_healthy
          ? t("adminPage.legacyRefresh.salesMonthly.notices.healthy")
          : t("adminPage.legacyRefresh.salesMonthly.notices.degraded", { count: result.missing_month_count }),
      );
    } catch (err) {
      setSalesMonthlyError(err instanceof Error ? err.message : t("adminPage.errors.loadFailed"));
    } finally {
      setSalesMonthlyLoading(false);
    }
  }

  async function refreshSalesMonthlyHealthAfterMutation() {
    const tenantId = salesMonthlyForm.tenantId.trim();
    if (!tenantId) {
      return;
    }
    const result = await fetchSalesMonthlyHealth(
      tenantId,
      salesMonthlyForm.startMonth || undefined,
      salesMonthlyForm.endMonth || undefined,
    );
    setSalesMonthlyHealth(result);
  }

  async function handleRepairMissingMonths() {
    const tenantId = salesMonthlyForm.tenantId.trim();
    const missingMonths = salesMonthlyHealth?.missing_months.map((item) => item.month_start) ?? [];
    if (!tenantId || missingMonths.length === 0) {
      return;
    }
    setSalesMonthlyAction("repair");
    setSalesMonthlyError(null);
    setSalesMonthlyNotice(null);
    try {
      const result = await repairSalesMonthlyMissing(tenantId, missingMonths);
      await refreshSalesMonthlyHealthAfterMutation();
      setSalesMonthlyNotice(
        t("adminPage.legacyRefresh.salesMonthly.notices.repaired", {
          count: result.refreshed_month_count,
        }),
      );
    } catch (err) {
      setSalesMonthlyError(err instanceof Error ? err.message : t("adminPage.errors.saveFailed"));
    } finally {
      setSalesMonthlyAction(null);
    }
  }

  async function handleBackfillRange() {
    const tenantId = salesMonthlyForm.tenantId.trim();
    if (!tenantId || !salesMonthlyForm.startMonth) {
      return;
    }
    setSalesMonthlyAction("backfill");
    setSalesMonthlyError(null);
    setSalesMonthlyNotice(null);
    try {
      const result: SalesMonthlyBackfillResponse = await backfillSalesMonthly(
        tenantId,
        salesMonthlyForm.startMonth,
        salesMonthlyForm.endMonth || undefined,
      );
      await refreshSalesMonthlyHealthAfterMutation();
      setSalesMonthlyNotice(
        t("adminPage.legacyRefresh.salesMonthly.notices.backfilled", {
          count: result.refreshed_month_count,
        }),
      );
    } catch (err) {
      setSalesMonthlyError(err instanceof Error ? err.message : t("adminPage.errors.saveFailed"));
    } finally {
      setSalesMonthlyAction(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("adminPage.legacyRefresh.eyebrow")}
        title={t("adminPage.legacyRefresh.title")}
        description={t("adminPage.legacyRefresh.description")}
      />

      {error ? <SurfaceMessage tone="danger">{error}</SurfaceMessage> : null}
      {triggerError && <SurfaceMessage tone="warning">{triggerError}</SurfaceMessage>}
      {triggerResult && !("conflict" in triggerResult) && (
        <SurfaceMessage tone="success">
          {t("adminPage.legacyRefresh.trigger.launched")}: {triggerResult.batch_id}
        </SurfaceMessage>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Trigger Control */}
        <SectionCard
          title={t("adminPage.legacyRefresh.trigger.title")}
          description={t("adminPage.legacyRefresh.trigger.description")}
        >
          <form className="space-y-4" onSubmit={handleTrigger}>
            <div className="space-y-2">
              <Label htmlFor="lr-tenant-id">{t("adminPage.legacyRefresh.fields.tenantId")}</Label>
              <Input
                id="lr-tenant-id"
                value={form.tenantId}
                onChange={(e) => setForm((f) => ({ ...f, tenantId: e.target.value }))}
                placeholder={t("adminPage.legacyRefresh.fields.tenantIdPlaceholder")}
                required
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="lr-schema-name">{t("adminPage.legacyRefresh.fields.schemaName")}</Label>
                <Input
                  id="lr-schema-name"
                  value={form.schemaName}
                  onChange={(e) => setForm((f) => ({ ...f, schemaName: e.target.value }))}
                  placeholder={t("adminPage.legacyRefresh.fields.schemaNamePlaceholder")}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="lr-source-schema">{t("adminPage.legacyRefresh.fields.sourceSchema")}</Label>
                <Input
                  id="lr-source-schema"
                  value={form.sourceSchema}
                  onChange={(e) => setForm((f) => ({ ...f, sourceSchema: e.target.value }))}
                  placeholder="public"
                />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="lr-mode">{t("adminPage.legacyRefresh.fields.mode")}</Label>
                <select
                  id="lr-mode"
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  value={form.mode}
                  onChange={(e) => setForm((f) => ({ ...f, mode: e.target.value as RefreshMode }))}
                >
                  <option value="incremental">{t("adminPage.legacyRefresh.modes.incremental")}</option>
                  <option value="full-rebaseline">{t("adminPage.legacyRefresh.modes.fullRebaseline")}</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="lr-lookback">{t("adminPage.legacyRefresh.fields.lookbackDays")}</Label>
                <Input
                  id="lr-lookback"
                  type="number"
                  min={0}
                  value={form.lookbackDays}
                  onChange={(e) => setForm((f) => ({ ...f, lookbackDays: parseInt(e.target.value) || 0 }))}
                />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="lr-threshold">{t("adminPage.legacyRefresh.fields.reconciliationThreshold")}</Label>
                <Input
                  id="lr-threshold"
                  type="number"
                  min={0}
                  value={form.reconciliationThreshold}
                  onChange={(e) => setForm((f) => ({ ...f, reconciliationThreshold: parseInt(e.target.value) || 0 }))}
                />
              </div>
              <div className="flex items-end pb-1">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={form.dryRun}
                    onChange={(e) => setForm((f) => ({ ...f, dryRun: e.target.checked }))}
                    className="h-4 w-4 rounded border-input"
                  />
                  {t("adminPage.legacyRefresh.fields.dryRun")}
                </label>
              </div>
            </div>
            <Button type="submit" disabled={triggerLoading || !form.tenantId || !form.schemaName}>
              {triggerLoading ? t("adminPage.legacyRefresh.trigger.launching") : t("adminPage.legacyRefresh.trigger.launch")}
            </Button>
          </form>
        </SectionCard>

        {/* Recent Runs */}
        <SectionCard
          title={t("adminPage.legacyRefresh.recentRuns.title")}
          description={t("adminPage.legacyRefresh.recentRuns.description")}
          actions={
            <Button variant="outline" size="sm" onClick={() => void loadRecentRuns()}>
              {t("adminPage.legacyRefresh.recentRuns.refresh")}
            </Button>
          }
        >
          {loading && recentRuns.length === 0 ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              {t("adminPage.legacyRefresh.loading")}
            </div>
          ) : (
            <RecentRunsTable runs={recentRuns} />
          )}
        </SectionCard>
      </div>

      <SectionCard
        title={t("adminPage.legacyRefresh.salesMonthly.title")}
        description={t("adminPage.legacyRefresh.salesMonthly.description")}
      >
        <div className="space-y-4">
          {salesMonthlyError ? <SurfaceMessage tone="danger">{salesMonthlyError}</SurfaceMessage> : null}
          {salesMonthlyNotice ? <SurfaceMessage tone="default">{salesMonthlyNotice}</SurfaceMessage> : null}

          <div className="grid gap-3 lg:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="lsm-tenant-id">{t("adminPage.legacyRefresh.salesMonthly.fields.tenantId")}</Label>
              <Input
                id="lsm-tenant-id"
                value={salesMonthlyForm.tenantId}
                onChange={(event) => setSalesMonthlyForm((current) => ({
                  ...current,
                  tenantId: event.target.value,
                }))}
                placeholder={t("adminPage.legacyRefresh.fields.tenantIdPlaceholder")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="lsm-start-month">{t("adminPage.legacyRefresh.salesMonthly.fields.startMonth")}</Label>
              <DatePicker
                id="lsm-start-month"
                value={parseDatePickerInputValue(salesMonthlyForm.startMonth)}
                onChange={(value) => setSalesMonthlyForm((current) => ({
                  ...current,
                  startMonth: serializeDatePickerValue(value),
                }))}
                placeholder={t("adminPage.legacyRefresh.salesMonthly.fields.startMonthPlaceholder")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="lsm-end-month">{t("adminPage.legacyRefresh.salesMonthly.fields.endMonth")}</Label>
              <DatePicker
                id="lsm-end-month"
                value={parseDatePickerInputValue(salesMonthlyForm.endMonth)}
                onChange={(value) => setSalesMonthlyForm((current) => ({
                  ...current,
                  endMonth: serializeDatePickerValue(value),
                }))}
                placeholder={t("adminPage.legacyRefresh.salesMonthly.fields.endMonthPlaceholder")}
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                void handleSalesMonthlyHealthCheck();
              }}
              disabled={salesMonthlyLoading || !salesMonthlyForm.tenantId.trim()}
            >
              {salesMonthlyLoading
                ? t("adminPage.legacyRefresh.salesMonthly.actions.checkingHealth")
                : t("adminPage.legacyRefresh.salesMonthly.actions.checkHealth")}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                void handleBackfillRange();
              }}
              disabled={salesMonthlyAction !== null || !salesMonthlyForm.tenantId.trim() || !salesMonthlyForm.startMonth}
            >
              {salesMonthlyAction === "backfill"
                ? t("adminPage.legacyRefresh.salesMonthly.actions.backfilling")
                : t("adminPage.legacyRefresh.salesMonthly.actions.backfill")}
            </Button>
            <Button
              type="button"
              onClick={() => {
                void handleRepairMissingMonths();
              }}
              disabled={salesMonthlyAction !== null || (salesMonthlyHealth?.missing_month_count ?? 0) === 0}
            >
              {salesMonthlyAction === "repair"
                ? t("adminPage.legacyRefresh.salesMonthly.actions.repairingMissing")
                : t("adminPage.legacyRefresh.salesMonthly.actions.repairMissing")}
            </Button>
          </div>

          {salesMonthlyHealth ? (
            <div className="space-y-3 rounded-xl border border-border/60 bg-muted/10 p-4 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={salesMonthlyHealth.is_healthy ? "success" : "warning"} className="normal-case tracking-normal">
                  {salesMonthlyHealth.is_healthy
                    ? t("adminPage.legacyRefresh.salesMonthly.status.healthy")
                    : t("adminPage.legacyRefresh.salesMonthly.status.degraded")}
                </Badge>
                <span className="text-muted-foreground">
                  {t("adminPage.legacyRefresh.salesMonthly.summary.checkedMonths", {
                    count: salesMonthlyHealth.checked_month_count,
                  })}
                </span>
                <span className="text-muted-foreground">
                  {t("adminPage.legacyRefresh.salesMonthly.summary.missingMonths", {
                    count: salesMonthlyHealth.missing_month_count,
                  })}
                </span>
                <span className="text-muted-foreground">
                  {t("adminPage.legacyRefresh.salesMonthly.summary.currentOpenMonth", {
                    month: salesMonthlyHealth.current_open_month,
                  })}
                </span>
              </div>

              {salesMonthlyHealth.missing_month_count === 0 ? (
                <p className="text-muted-foreground">
                  {t("adminPage.legacyRefresh.salesMonthly.empty")}
                </p>
              ) : (
                <ul className="space-y-2">
                  {salesMonthlyHealth.missing_months.map((item) => (
                    <li
                      key={item.month_start}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border/50 bg-background/70 px-3 py-2"
                    >
                      <span className="font-mono text-xs">{item.month_start}</span>
                      <span className="text-xs text-muted-foreground">
                        {item.transactional_order_count} orders · {item.transactional_revenue}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : null}
        </div>
      </SectionCard>

      {/* Lane Status Cards */}
      {lanes.length > 0 && (
        <SectionCard
          title={t("adminPage.legacyRefresh.lanes.title")}
          description={t("adminPage.legacyRefresh.lanes.description")}
          actions={
            <Button variant="outline" size="sm" onClick={() => void loadLanes()}>
              {t("adminPage.legacyRefresh.lanes.refresh")}
            </Button>
          }
        >
          <div className="space-y-3">
            {lanes.map((lane) => (
              <LaneStatusCard key={lane.lane_key} status={lane} />
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  );
}