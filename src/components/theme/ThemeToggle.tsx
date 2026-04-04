import { Monitor, MoonStar, SunMedium } from "lucide-react";

import { useTheme } from "./ThemeProvider";
import { Button } from "../ui/button";
import { cn } from "../../lib/utils";

const THEME_OPTIONS = [
  { value: "light", label: "Light", icon: SunMedium },
  { value: "dark", label: "Dark", icon: MoonStar },
  { value: "system", label: "System", icon: Monitor },
] as const;

export function ThemeToggle() {
  const { theme, resolvedTheme, setTheme } = useTheme();

  return (
    <div
      role="group"
      aria-label={`Theme mode. Current selection: ${theme === "system" ? `system (${resolvedTheme})` : theme}`}
      className="inline-flex items-center gap-1 rounded-full border border-border/80 bg-card/80 p-1 shadow-sm"
    >
      {THEME_OPTIONS.map((option) => {
        const Icon = option.icon;
        const isActive = theme === option.value;
        const resolvedSuffix = option.value === "system" ? `, currently ${resolvedTheme}` : "";

        return (
          <Button
            key={option.value}
            type="button"
            variant={isActive ? "default" : "ghost"}
            size="sm"
            className={cn("h-8 rounded-full px-2.5", isActive && "shadow-sm")}
            onClick={() => setTheme(option.value)}
            aria-pressed={isActive}
            aria-label={`Use ${option.label.toLowerCase()} theme${resolvedSuffix}`}
            title={`Use ${option.label.toLowerCase()} theme${resolvedSuffix}`}
          >
            <Icon className="size-4" />
            <span className="sr-only">{option.label}</span>
          </Button>
        );
      })}
    </div>
  );
}