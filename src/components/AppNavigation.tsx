import { ChevronRight, LogOut } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { useAuth } from "../hooks/useAuth";
import { usePermissions } from "../hooks/usePermissions";
import { NAVIGATION_GROUPS } from "../lib/navigation";
import { getInitials } from "../lib/utils";
import { ThemeToggle } from "./theme/ThemeToggle";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { Avatar, AvatarFallback } from "./ui/avatar";
import { Badge } from "./ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  useSidebar,
} from "./ui/sidebar";
import { Tooltip, TooltipContent, TooltipTrigger } from "./ui/tooltip";

export function AppNavigation() {
  const { t } = useTranslation("common");
  const { user, logout } = useAuth();
  const { canAccess } = usePermissions();
  const { open, isMobile } = useSidebar();

  const visibleGroups = NAVIGATION_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => canAccess(item.feature)),
  })).filter((group) => group.items.length > 0);

  const showLabel = open || isMobile;

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center gap-3 rounded-2xl border border-sidebar-border/70 bg-sidebar-accent/55 px-3 py-3">
          <div className="flex size-11 items-center justify-center rounded-2xl bg-primary/12 text-sm font-semibold text-primary">
            UE
          </div>
          {showLabel ? (
            <div className="min-w-0 space-y-1">
              <p className="text-sm font-semibold tracking-tight">UltrERP</p>
              <p className="text-xs text-sidebar-foreground/60">{t("app.tagline")}</p>
            </div>
          ) : null}
        </div>
      </SidebarHeader>

      <SidebarContent>
        {visibleGroups.map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel>{t(group.label)}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => {
                  const Icon = item.icon;

                  return (
                    <SidebarMenuItem key={item.to}>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <NavLink
                            to={item.to}
                            end={item.to === "/"}
                            className={({ isActive }) =>
                              [
                                "group flex items-center gap-3 rounded-2xl border px-3 py-2.5 text-sm font-medium transition-colors transition-shadow",
                                showLabel ? "justify-start" : "justify-center px-0",
                                isActive
                                  ? "border-sidebar-border bg-sidebar-accent text-sidebar-accent-foreground shadow-sm"
                                  : "border-transparent text-sidebar-foreground/72 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                              ].join(" ")
                            }
                          >
                            <Icon className="size-4 shrink-0" />
                            {showLabel ? (
                              <span className="flex min-w-0 flex-1 items-center justify-between gap-2">
                                <span className="truncate">{t(item.label)}</span>
                                <ChevronRight className="size-3.5 text-sidebar-foreground/40 transition-transform group-hover:translate-x-0.5" />
                              </span>
                            ) : null}
                          </NavLink>
                        </TooltipTrigger>
                        {!showLabel ? <TooltipContent side="right">{t(item.label)}</TooltipContent> : null}
                      </Tooltip>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter>
        <div className="space-y-3">
          <div className="rounded-2xl border border-sidebar-border/70 bg-sidebar-accent/45 px-3 py-3">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.28em] text-sidebar-foreground/60">
              {t("nav.language")}
            </p>
            <LanguageSwitcher />
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="flex w-full items-center gap-3 rounded-2xl border border-sidebar-border/70 bg-sidebar-accent/45 px-3 py-3 text-left transition-colors hover:bg-sidebar-accent/75"
              >
                <Avatar className="size-10 border border-sidebar-border/80">
                  <AvatarFallback>{getInitials(user?.sub ?? "")}</AvatarFallback>
                </Avatar>
                {showLabel ? (
                  <div className="min-w-0 flex-1 space-y-1">
                    <p className="truncate text-sm font-medium">{user?.sub ?? t("common.guest")}</p>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline" className="border-sidebar-border/80 bg-transparent text-[10px] text-sidebar-foreground/60">
                        {user?.role ?? t("common.guest")}
                      </Badge>
                      <span className="truncate text-xs text-sidebar-foreground/55">{user?.tenant_id ?? t("common.noTenant")}</span>
                    </div>
                  </div>
                ) : null}
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent side="top" align="end" className="w-60">
              <DropdownMenuLabel>{t("navMenu.workspace")}</DropdownMenuLabel>
              <DropdownMenuItem asChild>
                <div className="flex items-center justify-between gap-3 px-0 py-0 focus:bg-transparent">
                  <span className="px-2.5 py-2 text-sm">{t("navMenu.theme")}</span>
                  <ThemeToggle />
                </div>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={logout}>
                <LogOut className="size-4" />
                {t("navMenu.logOut")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}