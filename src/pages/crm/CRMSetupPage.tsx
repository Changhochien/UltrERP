import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { PageHeader, SectionCard, SurfaceMessage } from "../../components/layout/PageLayout";
import { Button } from "../../components/ui/button";
import { Checkbox } from "../../components/ui/checkbox";
import { Field, FieldLabel } from "../../components/ui/field";
import { Input } from "../../components/ui/input";
import { useAuth } from "../../hooks/useAuth";
import { useToast } from "../../hooks/useToast";
import { useCRMSetupBundle } from "../../domain/crm/hooks/useCRMSetupBundle";
import type {
  CRMCustomerGroup,
  CRMCustomerGroupPayload,
  CRMSettings,
  CRMSalesStage,
  CRMSalesStagePayload,
  CRMTerritory,
  CRMTerritoryPayload,
} from "../../domain/crm/types";
import {
  createCRMCustomerGroup,
  createCRMSalesStage,
  createCRMTerritory,
  updateCRMCustomerGroup,
  updateCRMSettings,
  updateCRMSalesStage,
  updateCRMTerritory,
} from "../../lib/api/crm";
import { CRM_SETUP_ROUTE, type AppRoute } from "../../lib/routes";

const SELECT_CLASS_NAME =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

function SalesStageEditor({
  stage,
  disabled,
  saving,
  onSave,
}: {
  stage: CRMSalesStage;
  disabled: boolean;
  saving: boolean;
  onSave: (payload: Partial<CRMSalesStagePayload>) => Promise<void>;
}) {
  const [name, setName] = useState(stage.name);
  const [probability, setProbability] = useState(String(stage.probability));
  const [sortOrder, setSortOrder] = useState(String(stage.sort_order));
  const [isActive, setIsActive] = useState(stage.is_active);

  useEffect(() => {
    setName(stage.name);
    setProbability(String(stage.probability));
    setSortOrder(String(stage.sort_order));
    setIsActive(stage.is_active);
  }, [stage]);

  return (
    <div className="grid gap-3 rounded-xl border border-border/70 bg-background/40 p-4 md:grid-cols-[minmax(0,1.6fr)_120px_120px_auto_auto] md:items-end">
      <Field>
        <FieldLabel htmlFor={`sales-stage-name-${stage.id}`}>Name</FieldLabel>
        <Input id={`sales-stage-name-${stage.id}`} value={name} onChange={(event) => setName(event.target.value)} disabled={disabled} />
      </Field>
      <Field>
        <FieldLabel htmlFor={`sales-stage-probability-${stage.id}`}>Probability</FieldLabel>
        <Input
          id={`sales-stage-probability-${stage.id}`}
          type="number"
          min="0"
          max="100"
          value={probability}
          onChange={(event) => setProbability(event.target.value)}
          disabled={disabled}
        />
      </Field>
      <Field>
        <FieldLabel htmlFor={`sales-stage-sort-${stage.id}`}>Sort</FieldLabel>
        <Input
          id={`sales-stage-sort-${stage.id}`}
          type="number"
          min="0"
          value={sortOrder}
          onChange={(event) => setSortOrder(event.target.value)}
          disabled={disabled}
        />
      </Field>
      <label className="flex items-center gap-2 text-sm text-foreground">
        <Checkbox checked={isActive} onCheckedChange={(checked) => setIsActive(Boolean(checked))} disabled={disabled} />
        Active
      </label>
      <Button
        type="button"
        variant="outline"
        onClick={() =>
          onSave({
            name,
            probability: Number(probability || 0),
            sort_order: Number(sortOrder || 0),
            is_active: isActive,
          })
        }
        disabled={disabled || saving}
      >
        {saving ? "Saving…" : "Save"}
      </Button>
    </div>
  );
}

function MasterNodeEditor({
  item,
  options,
  disabled,
  saving,
  onSave,
}: {
  item: CRMTerritory | CRMCustomerGroup;
  options: Array<CRMTerritory | CRMCustomerGroup>;
  disabled: boolean;
  saving: boolean;
  onSave: (payload: Partial<CRMTerritoryPayload | CRMCustomerGroupPayload>) => Promise<void>;
}) {
  const [name, setName] = useState(item.name);
  const [parentId, setParentId] = useState(item.parent_id ?? "");
  const [sortOrder, setSortOrder] = useState(String(item.sort_order));
  const [isGroup, setIsGroup] = useState(item.is_group);
  const [isActive, setIsActive] = useState(item.is_active);

  useEffect(() => {
    setName(item.name);
    setParentId(item.parent_id ?? "");
    setSortOrder(String(item.sort_order));
    setIsGroup(item.is_group);
    setIsActive(item.is_active);
  }, [item]);

  const parentOptions = useMemo(
    () => options.filter((option) => option.id !== item.id),
    [item.id, options],
  );

  return (
    <div className="grid gap-3 rounded-xl border border-border/70 bg-background/40 p-4 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_100px_auto_auto_auto] md:items-end">
      <Field>
        <FieldLabel htmlFor={`master-name-${item.id}`}>Name</FieldLabel>
        <Input id={`master-name-${item.id}`} value={name} onChange={(event) => setName(event.target.value)} disabled={disabled} />
      </Field>
      <Field>
        <FieldLabel htmlFor={`master-parent-${item.id}`}>Parent</FieldLabel>
        <select id={`master-parent-${item.id}`} className={SELECT_CLASS_NAME} value={parentId} onChange={(event) => setParentId(event.target.value)} disabled={disabled}>
          <option value="">None</option>
          {parentOptions.map((option) => (
            <option key={option.id} value={option.id}>{option.name}</option>
          ))}
        </select>
      </Field>
      <Field>
        <FieldLabel htmlFor={`master-sort-${item.id}`}>Sort</FieldLabel>
        <Input
          id={`master-sort-${item.id}`}
          type="number"
          min="0"
          value={sortOrder}
          onChange={(event) => setSortOrder(event.target.value)}
          disabled={disabled}
        />
      </Field>
      <label className="flex items-center gap-2 text-sm text-foreground">
        <Checkbox checked={isGroup} onCheckedChange={(checked) => setIsGroup(Boolean(checked))} disabled={disabled} />
        Group
      </label>
      <label className="flex items-center gap-2 text-sm text-foreground">
        <Checkbox checked={isActive} onCheckedChange={(checked) => setIsActive(Boolean(checked))} disabled={disabled} />
        Active
      </label>
      <Button
        type="button"
        variant="outline"
        onClick={() =>
          onSave({
            name,
            parent_id: parentId || null,
            sort_order: Number(sortOrder || 0),
            is_group: isGroup,
            is_active: isActive,
          })
        }
        disabled={disabled || saving}
      >
        {saving ? "Saving…" : "Save"}
      </Button>
    </div>
  );
}

export default function CRMSetupPage() {
  const { t } = useTranslation("common");
const { t: tRoutes } = useTranslation("routes");
  const { user } = useAuth();
  const { success: showSuccessToast, error: showErrorToast } = useToast();
  const { data, loading, error, reload } = useCRMSetupBundle();
  const isAdmin = user?.role === "admin" || user?.role === "owner";
  const [settingsDraft, setSettingsDraft] = useState<CRMSettings>(data.settings);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [newStage, setNewStage] = useState<CRMSalesStagePayload>({
    name: "",
    probability: 0,
    sort_order: 50,
    is_active: true,
  });
  const [newTerritory, setNewTerritory] = useState<CRMTerritoryPayload>({
    name: "",
    parent_id: null,
    is_group: false,
    sort_order: 50,
    is_active: true,
  });
  const [newCustomerGroup, setNewCustomerGroup] = useState<CRMCustomerGroupPayload>({
    name: "",
    parent_id: null,
    is_group: false,
    sort_order: 50,
    is_active: true,
  });

  useEffect(() => {
    setSettingsDraft(data.settings);
  }, [data.settings]);

  async function saveSettings() {
    setSettingsSaving(true);
    try {
      const result = await updateCRMSettings({
        lead_duplicate_policy: settingsDraft.lead_duplicate_policy,
        default_quotation_validity_days: Number(settingsDraft.default_quotation_validity_days),
        contact_creation_enabled: settingsDraft.contact_creation_enabled,
        carry_forward_communications: settingsDraft.carry_forward_communications,
        carry_forward_comments: settingsDraft.carry_forward_comments,
        opportunity_auto_close_days: settingsDraft.opportunity_auto_close_days,
      });
      if (result.ok) {
        showSuccessToast(t("crm.setup.settingsSavedTitle"), t("crm.setup.settingsSavedDescription"));
        reload();
        return;
      }
      showErrorToast(t("crm.setup.settingsErrorTitle"), result.errors[0]?.message ?? t("crm.setup.settingsErrorDescription"));
    } finally {
      setSettingsSaving(false);
    }
  }

  async function saveSalesStage(stageId: string, payload: Partial<CRMSalesStagePayload>) {
    setSavingKey(`stage:${stageId}`);
    try {
      const result = await updateCRMSalesStage(stageId, payload);
      if (result.ok) {
        showSuccessToast(t("crm.setup.masterSavedTitle"), t("crm.setup.masterSavedDescription"));
        reload();
        return;
      }
      showErrorToast(t("crm.setup.masterErrorTitle"), result.errors[0]?.message ?? t("crm.setup.masterErrorDescription"));
    } finally {
      setSavingKey(null);
    }
  }

  async function saveTerritory(territoryId: string, payload: Partial<CRMTerritoryPayload>) {
    setSavingKey(`territory:${territoryId}`);
    try {
      const result = await updateCRMTerritory(territoryId, payload);
      if (result.ok) {
        showSuccessToast(t("crm.setup.masterSavedTitle"), t("crm.setup.masterSavedDescription"));
        reload();
        return;
      }
      showErrorToast(t("crm.setup.masterErrorTitle"), result.errors[0]?.message ?? t("crm.setup.masterErrorDescription"));
    } finally {
      setSavingKey(null);
    }
  }

  async function saveCustomerGroup(customerGroupId: string, payload: Partial<CRMCustomerGroupPayload>) {
    setSavingKey(`customer-group:${customerGroupId}`);
    try {
      const result = await updateCRMCustomerGroup(customerGroupId, payload);
      if (result.ok) {
        showSuccessToast(t("crm.setup.masterSavedTitle"), t("crm.setup.masterSavedDescription"));
        reload();
        return;
      }
      showErrorToast(t("crm.setup.masterErrorTitle"), result.errors[0]?.message ?? t("crm.setup.masterErrorDescription"));
    } finally {
      setSavingKey(null);
    }
  }

  async function createStage() {
    setSavingKey("new-stage");
    try {
      const result = await createCRMSalesStage(newStage);
      if (result.ok) {
        setNewStage({ name: "", probability: 0, sort_order: 50, is_active: true });
        showSuccessToast(t("crm.setup.masterSavedTitle"), t("crm.setup.masterSavedDescription"));
        reload();
        return;
      }
      showErrorToast(t("crm.setup.masterErrorTitle"), result.errors[0]?.message ?? t("crm.setup.masterErrorDescription"));
    } finally {
      setSavingKey(null);
    }
  }

  async function createTerritory() {
    setSavingKey("new-territory");
    try {
      const result = await createCRMTerritory(newTerritory);
      if (result.ok) {
        setNewTerritory({ name: "", parent_id: null, is_group: false, sort_order: 50, is_active: true });
        showSuccessToast(t("crm.setup.masterSavedTitle"), t("crm.setup.masterSavedDescription"));
        reload();
        return;
      }
      showErrorToast(t("crm.setup.masterErrorTitle"), result.errors[0]?.message ?? t("crm.setup.masterErrorDescription"));
    } finally {
      setSavingKey(null);
    }
  }

  async function createCustomerGroup() {
    setSavingKey("new-customer-group");
    try {
      const result = await createCRMCustomerGroup(newCustomerGroup);
      if (result.ok) {
        setNewCustomerGroup({ name: "", parent_id: null, is_group: false, sort_order: 50, is_active: true });
        showSuccessToast(t("crm.setup.masterSavedTitle"), t("crm.setup.masterSavedDescription"));
        reload();
        return;
      }
      showErrorToast(t("crm.setup.masterErrorTitle"), result.errors[0]?.message ?? t("crm.setup.masterErrorDescription"));
    } finally {
      setSavingKey(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: tRoutes("crmSetup.label"), href: CRM_SETUP_ROUTE as AppRoute }]}
        eyebrow={t("crm.setup.eyebrow")}
        title={t("crm.setup.title")}
        description={t("crm.setup.description")}
      />

      {!isAdmin ? (
        <SurfaceMessage tone="warning">{t("crm.setup.adminOnlyNotice")}</SurfaceMessage>
      ) : null}
      {error ? <SurfaceMessage tone="warning">{error}</SurfaceMessage> : null}

      <SectionCard title={t("crm.setup.settingsTitle")} description={t("crm.setup.settingsDescription")}>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <Field>
            <FieldLabel htmlFor="lead_duplicate_policy">{t("crm.setup.duplicatePolicy")}</FieldLabel>
            <select
              id="lead_duplicate_policy"
              className={SELECT_CLASS_NAME}
              value={settingsDraft.lead_duplicate_policy}
              onChange={(event) => setSettingsDraft((current) => ({ ...current, lead_duplicate_policy: event.target.value as CRMSettings["lead_duplicate_policy"] }))}
              disabled={!isAdmin}
            >
              <option value="block">{t("crm.setup.duplicatePolicyBlock")}</option>
              <option value="allow">{t("crm.setup.duplicatePolicyAllow")}</option>
            </select>
          </Field>
          <Field>
            <FieldLabel htmlFor="default_quotation_validity_days">{t("crm.setup.defaultQuotationValidityDays")}</FieldLabel>
            <Input
              id="default_quotation_validity_days"
              type="number"
              min="1"
              value={settingsDraft.default_quotation_validity_days}
              onChange={(event) => setSettingsDraft((current) => ({ ...current, default_quotation_validity_days: Number(event.target.value || 1) }))}
              disabled={!isAdmin}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="opportunity_auto_close_days">{t("crm.setup.opportunityAutoCloseDays")}</FieldLabel>
            <Input
              id="opportunity_auto_close_days"
              type="number"
              min="1"
              value={settingsDraft.opportunity_auto_close_days ?? ""}
              onChange={(event) => setSettingsDraft((current) => ({ ...current, opportunity_auto_close_days: event.target.value ? Number(event.target.value) : null }))}
              disabled={!isAdmin}
            />
          </Field>
        </div>
        <div className="mt-4 flex flex-wrap gap-4 text-sm text-foreground">
          <label className="flex items-center gap-2">
            <Checkbox checked={settingsDraft.contact_creation_enabled} onCheckedChange={(checked) => setSettingsDraft((current) => ({ ...current, contact_creation_enabled: Boolean(checked) }))} disabled={!isAdmin} />
            {t("crm.setup.contactCreationEnabled")}
          </label>
          <label className="flex items-center gap-2">
            <Checkbox checked={settingsDraft.carry_forward_communications} onCheckedChange={(checked) => setSettingsDraft((current) => ({ ...current, carry_forward_communications: Boolean(checked) }))} disabled={!isAdmin} />
            {t("crm.setup.carryForwardCommunications")}
          </label>
          <label className="flex items-center gap-2">
            <Checkbox checked={settingsDraft.carry_forward_comments} onCheckedChange={(checked) => setSettingsDraft((current) => ({ ...current, carry_forward_comments: Boolean(checked) }))} disabled={!isAdmin} />
            {t("crm.setup.carryForwardComments")}
          </label>
        </div>
        <div className="mt-4 flex justify-end">
          <Button type="button" onClick={saveSettings} disabled={!isAdmin || settingsSaving}>
            {settingsSaving ? t("crm.setup.saving") : t("crm.setup.saveSettings")}
          </Button>
        </div>
      </SectionCard>

      <SectionCard title={t("crm.setup.salesStagesTitle")} description={t("crm.setup.salesStagesDescription")}>
        <div className="space-y-3">
          <div className="grid gap-3 rounded-xl border border-dashed border-border/70 bg-muted/20 p-4 md:grid-cols-[minmax(0,1.6fr)_120px_120px_auto_auto] md:items-end">
            <Field>
              <FieldLabel htmlFor="new-stage-name">Name</FieldLabel>
              <Input id="new-stage-name" value={newStage.name} onChange={(event) => setNewStage((current) => ({ ...current, name: event.target.value }))} disabled={!isAdmin} />
            </Field>
            <Field>
              <FieldLabel htmlFor="new-stage-probability">Probability</FieldLabel>
              <Input id="new-stage-probability" type="number" min="0" max="100" value={newStage.probability} onChange={(event) => setNewStage((current) => ({ ...current, probability: Number(event.target.value || 0) }))} disabled={!isAdmin} />
            </Field>
            <Field>
              <FieldLabel htmlFor="new-stage-sort">Sort</FieldLabel>
              <Input id="new-stage-sort" type="number" min="0" value={newStage.sort_order} onChange={(event) => setNewStage((current) => ({ ...current, sort_order: Number(event.target.value || 0) }))} disabled={!isAdmin} />
            </Field>
            <label className="flex items-center gap-2 text-sm text-foreground">
              <Checkbox checked={newStage.is_active} onCheckedChange={(checked) => setNewStage((current) => ({ ...current, is_active: Boolean(checked) }))} disabled={!isAdmin} />
              Active
            </label>
            <Button type="button" variant="outline" onClick={createStage} disabled={!isAdmin || savingKey === "new-stage"}>
              {savingKey === "new-stage" ? t("crm.setup.saving") : t("crm.setup.addMaster")}
            </Button>
          </div>
          {data.sales_stages.map((stage) => (
            <SalesStageEditor
              key={stage.id}
              stage={stage}
              disabled={!isAdmin}
              saving={savingKey === `stage:${stage.id}`}
              onSave={(payload) => saveSalesStage(stage.id, payload)}
            />
          ))}
        </div>
      </SectionCard>

      <SectionCard title={t("crm.setup.territoriesTitle")} description={t("crm.setup.territoriesDescription")}>
        <div className="space-y-3">
          <div className="grid gap-3 rounded-xl border border-dashed border-border/70 bg-muted/20 p-4 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_100px_auto_auto_auto] md:items-end">
            <Field>
              <FieldLabel htmlFor="new-territory-name">Name</FieldLabel>
              <Input id="new-territory-name" value={newTerritory.name} onChange={(event) => setNewTerritory((current) => ({ ...current, name: event.target.value }))} disabled={!isAdmin} />
            </Field>
            <Field>
              <FieldLabel htmlFor="new-territory-parent">Parent</FieldLabel>
              <select id="new-territory-parent" className={SELECT_CLASS_NAME} value={newTerritory.parent_id ?? ""} onChange={(event) => setNewTerritory((current) => ({ ...current, parent_id: event.target.value || null }))} disabled={!isAdmin}>
                <option value="">None</option>
                {data.territories.map((option) => (
                  <option key={option.id} value={option.id}>{option.name}</option>
                ))}
              </select>
            </Field>
            <Field>
              <FieldLabel htmlFor="new-territory-sort">Sort</FieldLabel>
              <Input id="new-territory-sort" type="number" min="0" value={newTerritory.sort_order} onChange={(event) => setNewTerritory((current) => ({ ...current, sort_order: Number(event.target.value || 0) }))} disabled={!isAdmin} />
            </Field>
            <label className="flex items-center gap-2 text-sm text-foreground">
              <Checkbox checked={newTerritory.is_group} onCheckedChange={(checked) => setNewTerritory((current) => ({ ...current, is_group: Boolean(checked) }))} disabled={!isAdmin} />
              Group
            </label>
            <label className="flex items-center gap-2 text-sm text-foreground">
              <Checkbox checked={newTerritory.is_active} onCheckedChange={(checked) => setNewTerritory((current) => ({ ...current, is_active: Boolean(checked) }))} disabled={!isAdmin} />
              Active
            </label>
            <Button type="button" variant="outline" onClick={createTerritory} disabled={!isAdmin || savingKey === "new-territory"}>
              {savingKey === "new-territory" ? t("crm.setup.saving") : t("crm.setup.addMaster")}
            </Button>
          </div>
          {data.territories.map((territory) => (
            <MasterNodeEditor
              key={territory.id}
              item={territory}
              options={data.territories}
              disabled={!isAdmin}
              saving={savingKey === `territory:${territory.id}`}
              onSave={(payload) => saveTerritory(territory.id, payload as Partial<CRMTerritoryPayload>)}
            />
          ))}
        </div>
      </SectionCard>

      <SectionCard title={t("crm.setup.customerGroupsTitle")} description={t("crm.setup.customerGroupsDescription")}>
        <div className="space-y-3">
          <div className="grid gap-3 rounded-xl border border-dashed border-border/70 bg-muted/20 p-4 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_100px_auto_auto_auto] md:items-end">
            <Field>
              <FieldLabel htmlFor="new-customer-group-name">Name</FieldLabel>
              <Input id="new-customer-group-name" value={newCustomerGroup.name} onChange={(event) => setNewCustomerGroup((current) => ({ ...current, name: event.target.value }))} disabled={!isAdmin} />
            </Field>
            <Field>
              <FieldLabel htmlFor="new-customer-group-parent">Parent</FieldLabel>
              <select id="new-customer-group-parent" className={SELECT_CLASS_NAME} value={newCustomerGroup.parent_id ?? ""} onChange={(event) => setNewCustomerGroup((current) => ({ ...current, parent_id: event.target.value || null }))} disabled={!isAdmin}>
                <option value="">None</option>
                {data.customer_groups.map((option) => (
                  <option key={option.id} value={option.id}>{option.name}</option>
                ))}
              </select>
            </Field>
            <Field>
              <FieldLabel htmlFor="new-customer-group-sort">Sort</FieldLabel>
              <Input id="new-customer-group-sort" type="number" min="0" value={newCustomerGroup.sort_order} onChange={(event) => setNewCustomerGroup((current) => ({ ...current, sort_order: Number(event.target.value || 0) }))} disabled={!isAdmin} />
            </Field>
            <label className="flex items-center gap-2 text-sm text-foreground">
              <Checkbox checked={newCustomerGroup.is_group} onCheckedChange={(checked) => setNewCustomerGroup((current) => ({ ...current, is_group: Boolean(checked) }))} disabled={!isAdmin} />
              Group
            </label>
            <label className="flex items-center gap-2 text-sm text-foreground">
              <Checkbox checked={newCustomerGroup.is_active} onCheckedChange={(checked) => setNewCustomerGroup((current) => ({ ...current, is_active: Boolean(checked) }))} disabled={!isAdmin} />
              Active
            </label>
            <Button type="button" variant="outline" onClick={createCustomerGroup} disabled={!isAdmin || savingKey === "new-customer-group"}>
              {savingKey === "new-customer-group" ? t("crm.setup.saving") : t("crm.setup.addMaster")}
            </Button>
          </div>
          {data.customer_groups.map((customerGroup) => (
            <MasterNodeEditor
              key={customerGroup.id}
              item={customerGroup}
              options={data.customer_groups}
              disabled={!isAdmin}
              saving={savingKey === `customer-group:${customerGroup.id}`}
              onSave={(payload) => saveCustomerGroup(customerGroup.id, payload as Partial<CRMCustomerGroupPayload>)}
            />
          ))}
        </div>
      </SectionCard>

      {loading ? <SurfaceMessage>{t("crm.setup.loading")}</SurfaceMessage> : null}
    </div>
  );
}
