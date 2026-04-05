import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Eye, EyeOff } from "lucide-react";

import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";
import { Switch } from "../ui/switch";
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
  onSave: (key: string, value: string) => Promise<void>;
  onReset: (key: string) => Promise<void>;
  saving?: boolean;
  resetting?: boolean;
}

export function SettingField({
  item,
  onSave,
  onReset,
  saving = false,
  resetting = false,
}: SettingFieldProps) {
  const { t } = useTranslation("common");
  const [localValue, setLocalValue] = useState(item.is_null ? "" : item.value);
  const [showPassword, setShowPassword] = useState(false);

  const hasChanged = localValue !== item.value;
  const displayValue = item.is_null ? "" : item.value;

  function handleSave() {
    void onSave(item.key, localValue);
  }

  function handleReset() {
    void onReset(item.key);
  }

  function renderInput() {
    // Sensitive fields render as password with visibility toggle
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
          >
            {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </button>
        </div>
      );
    }

    // Nullable null state
    if (item.nullable && item.is_null) {
      return (
        <Input
          type="text"
          placeholder="(empty)"
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
          <div className="flex items-center gap-3">
            <Switch
              checked={isTrue}
              onCheckedChange={(checked) => setLocalValue(checked ? "true" : "false")}
              disabled={saving}
            />
            <span className="text-sm text-muted-foreground">
              {isTrue ? "true" : "false"}
            </span>
          </div>
        );
      }

      case "int":
        return (
          <Input
            type="number"
            value={displayValue}
            onChange={(e) => setLocalValue(e.target.value)}
            disabled={saving}
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
            rows={4}
            placeholder="JSON array, e.g. ['https://example.com']"
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
    <div className="space-y-2">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1 flex-1">
          <Label>{item.key}</Label>
          {item.description ? (
            <p className="text-xs text-muted-foreground">{item.description}</p>
          ) : null}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {hasChanged ? (
            <Button
              type="button"
              size="sm"
              onClick={handleSave}
              disabled={saving}
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
          >
            {resetting ? t("common.loading") : t("common.reset") ?? "Reset"}
          </Button>
        </div>
      </div>
      {renderInput()}
    </div>
  );
}
