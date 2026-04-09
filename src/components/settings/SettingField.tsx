import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Eye, EyeOff } from "lucide-react";

import { Button } from "../ui/button";
import { Input } from "../ui/input";
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
            placeholder="JSON array, e.g. ['https://example.com']"
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

  const isMultiLine = item.value_type === "tuple" || item.value_type === "json";

  return (
    <div
      className={
        isMultiLine
          ? "flex flex-col gap-3 sm:flex-row sm:items-start"
          : "flex flex-col sm:flex-row sm:items-center"
      }
    >
      {/* Left: label + description — flex-1 takes all remaining space, pushing controls right */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground">{item.key}</p>
        {item.description ? (
          <p className="text-xs text-muted-foreground leading-relaxed mt-0.5">
            {item.description}
          </p>
        ) : null}
      </div>

      {/* Right: input + buttons — fixed 360px on all rows so right edges align across the form */}
      <div className="w-full sm:w-[360px] shrink-0 flex flex-col gap-3">
        <div className="flex items-center gap-3">
          {renderInput()}
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
              {resetting ? t("common.loading") : t("common.reset")}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
