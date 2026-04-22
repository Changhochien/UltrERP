import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Eye,
  EyeOff,
  ToggleLeft,
  Hash,
  List,
  Braces,
  Type,
  Shield,
} from "lucide-react";

import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { Switch } from "../ui/switch";
import { Badge } from "../ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import type { SettingItem } from "../../lib/api/settings";

interface SettingFieldProps {
  item: SettingItem;
  onSave: (key: string, value: string, valueType: string) => Promise<void>;
  onReset: (key: string) => Promise<void>;
  saving?: boolean;
  resetting?: boolean;
  error?: string | null;
}

/** Convert a setting key to a display title */
function getSettingKeyTitle(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Get translated title for a setting key, falling back to title case */
function translateSettingKey(t: (key: string, options?: Record<string, unknown>) => string, key: string): string {
  const translated = t(`settingsPage.keys.${key}`, { defaultValue: '' });
  return translated || getSettingKeyTitle(key);
}

/** Get icon and badge variant for each value type */
function getSettingTypeInfo(valueType: string, t: (key: string) => string): { icon: React.ReactNode; label: string; variant: "default" | "secondary" | "outline" } {
  switch (valueType) {
    case "bool":
      return { icon: <ToggleLeft className="size-3.5" />, label: t("settingsPage.types.bool"), variant: "secondary" };
    case "int":
      return { icon: <Hash className="size-3.5" />, label: t("settingsPage.types.int"), variant: "outline" };
    case "literal":
      return { icon: <List className="size-3.5" />, label: t("settingsPage.types.literal"), variant: "default" };
    case "json":
    case "tuple":
      return { icon: <Braces className="size-3.5" />, label: valueType === "json" ? t("settingsPage.types.json") : t("settingsPage.types.tuple"), variant: "outline" };
    case "str":
    default:
      return { icon: <Type className="size-3.5" />, label: t("settingsPage.types.str"), variant: "default" };
  }
}

export function SettingField({
  item,
  onSave,
  onReset,
  saving = false,
  resetting = false,
  error,
}: SettingFieldProps) {
  const { t } = useTranslation("common");
  const [localValue, setLocalValue] = useState(item.is_null ? "" : item.value);
  const [showPassword, setShowPassword] = useState(false);

  const hasChanged = localValue !== item.value;
  const displayValue = item.is_null ? "" : item.value;
  const typeInfo = getSettingTypeInfo(item.value_type, t);

  function handleSave() {
    void onSave(item.key, localValue, item.value_type);
  }

  function handleReset() {
    void onReset(item.key);
  }

  function renderInput() {
    if (item.is_sensitive) {
      return (
        <div className="relative">
          <Input
            type={showPassword ? "text" : "password"}
            value={displayValue}
            onChange={(e) => setLocalValue(e.target.value)}
            disabled={saving}
            className="pr-10"
          />
          <button
            type="button"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            onClick={() => setShowPassword((v) => !v)}
            tabIndex={-1}
            aria-label={showPassword ? t("settingsPage.hidePassword") : t("settingsPage.showPassword")}
          >
            {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </button>
        </div>
      );
    }

    if (item.nullable && item.is_null) {
      return (
        <Input
          type="text"
          placeholder={t("settingsPage.emptyPlaceholder")}
          value=""
          onChange={(e) => setLocalValue(e.target.value)}
          disabled={saving}
        />
      );
    }

    switch (item.value_type) {
      case "bool": {
        const isTrue =
          displayValue === "true" ||
          displayValue === "1" ||
          displayValue === "yes";
        return (
          <Switch
            checked={isTrue}
            onCheckedChange={(checked) => setLocalValue(checked ? "true" : "false")}
            disabled={saving}
          />
        );
      }

      case "int":
        return (
          <Input
            type="number"
            value={displayValue}
            onChange={(e) => setLocalValue(e.target.value)}
            disabled={saving}
            className="w-28"
          />
        );

      case "literal":
        return (
          <Select
            value={displayValue}
            onValueChange={(v) => setLocalValue(v)}
            disabled={saving}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(item.allowed_values ?? []).map((val) => (
                <SelectItem key={val} value={val}>
                  {val}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );

      case "tuple":
      case "json":
        return (
          <Textarea
            value={displayValue}
            onChange={(e) => setLocalValue(e.target.value)}
            disabled={saving}
            rows={3}
            placeholder={t("settingsPage.jsonPlaceholder")}
            className="resize-y"
          />
        );

      case "str":
      default:
        return (
          <Input
            type="text"
            value={displayValue}
            onChange={(e) => setLocalValue(e.target.value)}
            disabled={saving}
          />
        );
    }
  }

  return (
    <div className="group relative rounded-xl border border-border/60 bg-card/50 p-5 transition-all hover:border-border/80 hover:bg-card/70">
      {/* Header row: title, badges, and description */}
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-sm font-semibold text-foreground">
              {translateSettingKey(t, item.key)}
            </h4>
            <Badge variant={typeInfo.variant} className="gap-1 py-0 text-[10px] font-medium">
              {typeInfo.icon}
              {typeInfo.label}
            </Badge>
            {item.is_sensitive && (
              <Badge variant="destructive" className="gap-1 py-0 text-[10px] font-medium">
                <Shield className="size-3" />
                {t("settingsPage.sensitive")}
              </Badge>
            )}
            {item.nullable && (
              <Badge variant="outline" className="py-0 text-[10px] font-medium">
                {t("settingsPage.nullable")}
              </Badge>
            )}
          </div>
          {item.description ? (
            <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
              {item.description}
            </p>
          ) : null}
          {item.updated_at && (
            <p className="mt-1.5 text-[10px] text-muted-foreground/60">
              {t("settingsPage.lastUpdated")}: {new Date(item.updated_at).toLocaleDateString()}
              {item.updated_by ? ` ${t("settingsPage.by")} ${item.updated_by}` : ""}
            </p>
          )}
        </div>
      </div>

      {/* Input row */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex-1 min-w-0">
          {renderInput()}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {hasChanged ? (
            <Button
              type="button"
              size="sm"
              onClick={handleSave}
              disabled={saving}
              className="h-9 rounded-full px-4"
            >
              {saving ? t("common.loading") : t("common.save")}
            </Button>
          ) : null}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleReset}
            disabled={resetting || item.is_null}
            className="h-9 rounded-full px-3"
            title={item.is_null ? undefined : `${t("settingsPage.resetTitle")}: ${item.value}`}
          >
            {resetting ? t("common.loading") : t("common.reset")}
          </Button>
        </div>
      </div>

      {error && (
        <p className="mt-3 text-xs text-destructive flex items-center gap-1.5">
          <span className="inline-block h-1 w-1 rounded-full bg-destructive" />
          {error}
        </p>
      )}
    </div>
  );
}
