import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { DataTable } from "../components/layout/DataTable";
import { PageHeader, SectionCard, SurfaceMessage } from "../components/layout/PageLayout";
import { Badge } from "../components/ui/badge";
import { buttonVariants, Button } from "../components/ui/button";
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
import { Skeleton } from "../components/ui/skeleton";
import { cn } from "../lib/utils";
import { SETTINGS_ROUTE } from "../lib/routes";
import {
  ADMIN_USER_ROLES,
  ADMIN_USER_STATUSES,
  createUser,
  fetchAuditLogs,
  fetchUsers,
  type AdminUser,
  type AdminUserCreateRequest,
  type AdminUserRole,
  type AdminUserStatus,
  type AdminUserUpdateRequest,
  type AuditLogEntry,
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
  action: string;
  entityType: string;
  entityId: string;
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
  action: "",
  entityType: "",
  entityId: "",
};

const AUDIT_PAGE_SIZE = 20;
const MATRIX_ROLES: MatrixRole[] = ["admin", "owner", "finance", "warehouse", "sales"];
const AUDIT_ACTION_SUGGESTIONS = [
  "user.create",
  "user.update",
  "approval.approve",
  "approval.reject",
  "inventory.adjust",
  "product.update",
];
const AUDIT_ENTITY_SUGGESTIONS = [
  "user",
  "approval",
  "inventory_stock",
  "product",
  "settings",
];

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
      setUsers(await fetchUsers());
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
        entity_type: auditFilters.entityType || undefined,
        entity_id: auditFilters.entityId || undefined,
      });
      setAuditLogs(response.items);
      setAuditTotal(response.total);
    } catch (err) {
      setAuditError(err instanceof Error ? err.message : t("adminPage.errors.loadFailed"));
    } finally {
      setAuditLoading(false);
    }
  }, [auditFilters.action, auditFilters.actorId, auditFilters.entityId, auditFilters.entityType, auditPage, t]);

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
          >
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
                <Label htmlFor="admin-audit-action">{t("adminPage.auditLog.filters.action")}</Label>
                <Input
                  id="admin-audit-action"
                  list="admin-audit-action-list"
                  value={auditFilters.action}
                  onChange={(event) => updateAuditFilter("action", event.target.value)}
                  placeholder={t("adminPage.auditLog.filters.actionPlaceholder")}
                />
                <datalist id="admin-audit-action-list">
                  {AUDIT_ACTION_SUGGESTIONS.map((action) => (
                    <option key={action} value={action} />
                  ))}
                </datalist>
              </div>
              <div className="space-y-2">
                <Label htmlFor="admin-audit-entity-type">{t("adminPage.auditLog.filters.entityType")}</Label>
                <Input
                  id="admin-audit-entity-type"
                  list="admin-audit-entity-type-list"
                  value={auditFilters.entityType}
                  onChange={(event) => updateAuditFilter("entityType", event.target.value)}
                  placeholder={t("adminPage.auditLog.filters.entityTypePlaceholder")}
                />
                <datalist id="admin-audit-entity-type-list">
                  {AUDIT_ENTITY_SUGGESTIONS.map((entityType) => (
                    <option key={entityType} value={entityType} />
                  ))}
                </datalist>
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
            </div>

            <DataTable
              columns={[
                {
                  id: "created_at",
                  header: t("adminPage.auditLog.columns.createdAt"),
                  sortable: true,
                  getSortValue: (entry) => new Date(entry.created_at).getTime(),
                  cell: (entry) => new Date(entry.created_at).toLocaleString(),
                },
                {
                  id: "actor_id",
                  header: t("adminPage.auditLog.columns.actor"),
                  sortable: true,
                  getSortValue: (entry) => entry.actor_id,
                  cell: (entry) => entry.actor_id,
                },
                {
                  id: "action",
                  header: t("adminPage.auditLog.columns.action"),
                  sortable: true,
                  getSortValue: (entry) => entry.action,
                  cell: (entry) => entry.action,
                },
                {
                  id: "target",
                  header: t("adminPage.auditLog.columns.target"),
                  sortable: true,
                  getSortValue: (entry) => `${entry.entity_type}:${entry.entity_id}`,
                  cell: (entry) => `${entry.entity_type}:${entry.entity_id}`,
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
    </>
  );
}