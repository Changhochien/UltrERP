import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { PageHeader, PageTabs, SectionCard } from "../../components/layout/PageLayout";
import { Button } from "../../components/ui/button";
import type { PhysicalCountSession } from "../../domain/inventory/types";
import {
  approvePhysicalCountSession,
  fetchPhysicalCountSession,
  submitPhysicalCountSession,
  updatePhysicalCountLine,
} from "../../lib/api/inventory";
import { INVENTORY_COUNT_SESSIONS_ROUTE } from "../../lib/routes";
import { buildInventorySectionTabs, getInventorySectionRoute, type InventorySectionTabValue } from "./inventoryPageTabs";

type DraftMap = Record<string, { countedQty: string; notes: string }>;

function buildDrafts(session: PhysicalCountSession): DraftMap {
  return Object.fromEntries(
    session.lines.map((line) => [
      line.id,
      {
        countedQty: line.counted_qty == null ? "" : String(line.counted_qty),
        notes: line.notes ?? "",
      },
    ]),
  );
}

export function CountSessionDetailPage() {
  const { t } = useTranslation("common", { keyPrefix: "inventory.countSessionDetailPage" });
  const { t: tCommon } = useTranslation("common");
  const navigate = useNavigate();
  const params = useParams<{ sessionId: string }>();
  const sessionId = params.sessionId ?? "";
  const inventoryTabs = buildInventorySectionTabs(tCommon);

  const [session, setSession] = useState<PhysicalCountSession | null>(null);
  const [drafts, setDrafts] = useState<DraftMap>({});
  const [loading, setLoading] = useState(true);
  const [savingLineId, setSavingLineId] = useState<string | null>(null);
  const [sessionAction, setSessionAction] = useState<"submit" | "approve" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchPhysicalCountSession(sessionId)
      .then((result) => {
        if (cancelled) {
          return;
        }
        if (!result.ok) {
          setSession(null);
          setError(result.error);
          return;
        }
        setSession(result.data);
        setDrafts(buildDrafts(result.data));
      })
      .catch((loadError) => {
        if (!cancelled) {
          setSession(null);
          setError(loadError instanceof Error ? loadError.message : t("loadError"));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId, t]);

  const isEditable = session?.status === "in_progress";
  const canSubmit = session?.status === "in_progress" && session.counted_lines === session.total_lines;
  const canApprove = session?.status === "submitted";

  const summaryItems = useMemo(() => {
    if (!session) {
      return [];
    }
    return [
      { label: t("summary.status"), value: t(`status.${session.status}`) },
      { label: t("summary.warehouse"), value: session.warehouse_name ?? t("unknownWarehouse") },
      { label: t("summary.countedLines"), value: t("countedProgress", { counted: session.counted_lines, total: session.total_lines }) },
      { label: t("summary.varianceTotal"), value: String(session.variance_total) },
    ];
  }, [session, t]);

  async function handleSaveLine(lineId: string) {
    const draft = drafts[lineId];
    const normalizedCountedQty = draft?.countedQty?.trim() ?? "";
    if (normalizedCountedQty === "") {
      setError(t("invalidQuantity"));
      return;
    }

    const countedQty = Number(normalizedCountedQty);
    if (!Number.isInteger(countedQty) || countedQty < 0) {
      setError(t("invalidQuantity"));
      return;
    }

    setSavingLineId(lineId);
    setError(null);
    const result = await updatePhysicalCountLine(sessionId, lineId, {
      counted_qty: countedQty,
      notes: draft?.notes?.trim() || undefined,
    });
    setSavingLineId(null);

    if (!result.ok) {
      setError(result.error);
      return;
    }

    setSession(result.data);
    setDrafts(buildDrafts(result.data));
  }

  async function handleSubmitSession() {
    setSessionAction("submit");
    setError(null);
    const result = await submitPhysicalCountSession(sessionId);
    setSessionAction(null);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    setSession(result.data);
    setDrafts(buildDrafts(result.data));
  }

  async function handleApproveSession() {
    setSessionAction("approve");
    setError(null);
    const result = await approvePhysicalCountSession(sessionId);
    setSessionAction(null);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    setSession(result.data);
    setDrafts(buildDrafts(result.data));
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("eyebrow")}
        title={session ? t("title", { id: session.id.slice(0, 8) }) : t("titleLoading")}
        description={t("description")}
        actions={(
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" variant="outline" onClick={() => navigate(INVENTORY_COUNT_SESSIONS_ROUTE)}>
              {t("backToList")}
            </Button>
          </div>
        )}
        tabs={(
          <PageTabs
            items={inventoryTabs}
            value="count-sessions"
            ariaLabel={tCommon("inventory.page.title")}
            onValueChange={(next) => navigate(getInventorySectionRoute(next as InventorySectionTabValue))}
          />
        )}
      />

      {error ? <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div> : null}

      {loading ? (
        <SectionCard title={t("loadingTitle")} description={t("loading")}>
          <p className="text-sm text-muted-foreground">{t("loading")}</p>
        </SectionCard>
      ) : session == null ? (
        <SectionCard title={t("missingTitle")} description={t("missingDescription")} />
      ) : (
        <>
          <SectionCard title={t("summaryTitle")} description={t("summaryDescription")}>
            <div className="grid gap-4 md:grid-cols-4">
              {summaryItems.map((item) => (
                <div key={item.label} className="rounded-xl border border-border/70 bg-muted/20 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground">{item.label}</p>
                  <p className="mt-2 text-lg font-semibold">{item.value}</p>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard
            title={t("linesTitle")}
            description={isEditable ? t("linesDescriptionEditable") : t("linesDescriptionReadonly")}
            actions={(
              <div className="flex flex-wrap items-center gap-2">
                <Button type="button" onClick={() => void handleSubmitSession()} disabled={!canSubmit || sessionAction !== null}>
                  {sessionAction === "submit" ? t("submitting") : t("submit")}
                </Button>
                <Button type="button" variant="outline" onClick={() => void handleApproveSession()} disabled={!canApprove || sessionAction !== null}>
                  {sessionAction === "approve" ? t("approving") : t("approve")}
                </Button>
              </div>
            )}
          >
            <div className="overflow-x-auto rounded-xl border border-border/70">
              <table className="min-w-full divide-y divide-border/70 text-sm">
                <thead className="bg-muted/30 text-left text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3 font-medium">{t("columns.product")}</th>
                    <th className="px-4 py-3 font-medium">{t("columns.snapshot")}</th>
                    <th className="px-4 py-3 font-medium">{t("columns.counted")}</th>
                    <th className="px-4 py-3 font-medium">{t("columns.variance")}</th>
                    <th className="px-4 py-3 font-medium">{t("columns.notes")}</th>
                    <th className="px-4 py-3 font-medium">{t("columns.actions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {session.lines.map((line) => {
                    const draft = drafts[line.id] ?? { countedQty: "", notes: "" };
                    return (
                      <tr key={line.id}>
                        <td className="px-4 py-3 font-medium">
                          <div>{line.product_name ?? line.product_code ?? line.product_id}</div>
                          {line.product_code ? <div className="text-xs text-muted-foreground">{line.product_code}</div> : null}
                        </td>
                        <td className="px-4 py-3 font-mono">{line.system_qty_snapshot}</td>
                        <td className="px-4 py-3">
                          {isEditable ? (
                            <input
                              type="number"
                              min={0}
                              value={draft.countedQty}
                              onChange={(event) => setDrafts((current) => ({
                                ...current,
                                [line.id]: {
                                  countedQty: event.target.value,
                                  notes: current[line.id]?.notes ?? draft.notes,
                                },
                              }))}
                              className="w-24 rounded-lg border border-input bg-background px-3 py-2"
                            />
                          ) : (
                            <span className="font-mono">{line.counted_qty ?? "—"}</span>
                          )}
                        </td>
                        <td className="px-4 py-3 font-mono">{line.variance_qty ?? "—"}</td>
                        <td className="px-4 py-3">
                          {isEditable ? (
                            <textarea
                              value={draft.notes}
                              onChange={(event) => setDrafts((current) => ({
                                ...current,
                                [line.id]: {
                                  countedQty: current[line.id]?.countedQty ?? draft.countedQty,
                                  notes: event.target.value,
                                },
                              }))}
                              className="min-h-20 w-full rounded-lg border border-input bg-background px-3 py-2"
                            />
                          ) : (
                            <span>{line.notes ?? "—"}</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {isEditable ? (
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => void handleSaveLine(line.id)}
                              disabled={savingLineId === line.id}
                            >
                              {savingLineId === line.id ? t("savingLine") : t("saveLine")}
                            </Button>
                          ) : (
                            <span className="text-sm text-muted-foreground">{t("readonly")}</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </SectionCard>
        </>
      )}
    </div>
  );
}
