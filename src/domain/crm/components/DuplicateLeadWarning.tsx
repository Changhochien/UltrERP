import { useTranslation } from "react-i18next";

import type { DuplicateLeadCandidate, DuplicateLeadInfo } from "@/domain/crm/types";
import { Button } from "@/components/ui/button";

export interface DuplicateLeadWarningProps {
  duplicate: DuplicateLeadInfo;
  onOpenCandidate: (candidate: DuplicateLeadCandidate) => void;
  onCancel: () => void;
}

function kindLabelKey(kind: DuplicateLeadCandidate["kind"]) {
  return kind === "lead" ? "crm.duplicateWarning.kindLead" : "crm.duplicateWarning.kindCustomer";
}

function matchLabelKey(field: DuplicateLeadCandidate["matched_on"]) {
  if (field === "company_name") return "crm.duplicateWarning.matchCompanyName";
  if (field === "email_id") return "crm.duplicateWarning.matchEmail";
  return "crm.duplicateWarning.matchPhone";
}

export default function DuplicateLeadWarning({
  duplicate,
  onOpenCandidate,
  onCancel,
}: DuplicateLeadWarningProps) {
  const { t } = useTranslation("common");

  return (
    <div className="space-y-4 rounded-xl border border-warning/40 bg-warning/10 p-4 text-sm text-foreground" role="alert">
      <div className="space-y-1">
        <h3 className="text-base font-semibold">{t("crm.duplicateWarning.title")}</h3>
        <p className="text-muted-foreground">{t("crm.duplicateWarning.description")}</p>
      </div>

      <div className="space-y-3">
        {duplicate.candidates.map((candidate) => (
          <div key={`${candidate.kind}-${candidate.id}`} className="rounded-lg border border-border/70 bg-background/70 px-3 py-3">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-medium">{candidate.label}</p>
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                  {t(kindLabelKey(candidate.kind))} · {t(matchLabelKey(candidate.matched_on))}
                </p>
              </div>
              <Button type="button" size="sm" onClick={() => onOpenCandidate(candidate)}>
                {candidate.kind === "lead"
                  ? t("crm.duplicateWarning.openLead")
                  : t("crm.duplicateWarning.openCustomer")}
              </Button>
            </div>
          </div>
        ))}
      </div>

      <Button type="button" size="sm" variant="outline" onClick={onCancel}>
        {t("crm.duplicateWarning.continueEditing")}
      </Button>
    </div>
  );
}
