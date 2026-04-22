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
      className="inline-flex items-center gap-1 rounded-lg border border-sidebar-border/50 bg-sidebar-accent/40 p-1"
    >
      {THEME_OPTIONS.map((option) => {
        const Icon = option.icon;
        const isActive = theme === option.value;
        const resolvedSuffix = option.value === "system" ? `, currently ${resolvedTheme}` : "";

        return (
          <Button
            key={option.value}
            type="button"
            variant={isActive ? "secondary" : "ghost"}
            size="sm"
            className={cn(
              "h-7 rounded-md px-2 transition-colors",
              isActive
                ? "bg-sidebar-accent text-sidebar-accent-foreground shadow-sm"
                : "text-sidebar-muted hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
            )}
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
