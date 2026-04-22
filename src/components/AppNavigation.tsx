import * as React from "react";
import { ChevronDown, ChevronRight, LogOut } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { useAuth } from "../hooks/useAuth";
import { usePermissions } from "../hooks/usePermissions";
import { NAVIGATION_GROUPS, type NavigationSectionType } from "../lib/navigation";
import { cn, getInitials } from "../lib/utils";
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
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarSectionHeader,
  useSidebar,
} from "./ui/sidebar";
import { Tooltip, TooltipContent, TooltipTrigger } from "./ui/tooltip";

export function AppNavigation() {
  const { t } = useTranslation("common");
  const { user, logout } = useAuth();
  const { canAccess } = usePermissions();
  const { open, openMobile, isMobile, setOpenMobile, isSectionCollapsed, toggleSection, isGroupCollapsed, toggleGroup } = useSidebar();

  // Filter sections by permission, then filter out groups with no visible sections
  const visibleGroups = NAVIGATION_GROUPS.map((group) => ({
    ...group,
    sections: group.sections
      .map((section) => ({
        ...section,
        items: section.items.filter((item) => canAccess(item.feature)),
      }))
      .filter((section) => section.items.length > 0),
  })).filter((group) => group.sections.length > 0);

  const showLabel = isMobile ? openMobile : open;

  const handleNavigation = () => {
    if (isMobile) {
      setOpenMobile(false);
    }
  };

  // Get indentation class based on section type
  const getSectionIndentClass = (sectionType: NavigationSectionType): string => {
    if (sectionType === 'reports' || sectionType === 'setup') {
      return "pl-6";
    }
    return "";
  };

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center gap-3 rounded-xl border border-sidebar-border/50 bg-sidebar-accent/40 px-3 py-3">
          <div className="flex size-11 items-center justify-center rounded-xl bg-sidebar-accent/80 text-sm font-semibold text-sidebar-accent-foreground">
            UE
          </div>
          {showLabel ? (
            <div className="min-w-0 space-y-1">
              <p className="text-sm font-semibold tracking-tight text-sidebar-foreground">UltrERP</p>
              <p className="text-xs text-sidebar-muted">{t("app.tagline")}</p>
            </div>
          ) : null}
        </div>
      </SidebarHeader>

      <SidebarContent>
        {visibleGroups.map((group) => {
          const groupCollapsed = isGroupCollapsed(group.label);
          
          return (
            <SidebarGroup key={group.label}>
              {/* Collapsible group header */}
              <button
                type="button"
                onClick={() => toggleGroup(group.label)}
                className={cn(
                  "mb-2 flex w-full items-center justify-between px-2 text-[11px] font-semibold uppercase tracking-[0.2em] transition-colors",
                  "text-sidebar-foreground/80",
                )}
              >
                <span>{t(group.label)}</span>
                <ChevronDown
                  className={cn(
                    "size-3 text-sidebar-foreground/60 transition-transform duration-200",
                    groupCollapsed ? "-rotate-90" : "rotate-0",
                  )}
                />
              </button>
              
              {/* Group content - collapsible */}
              {!groupCollapsed && (
                <SidebarGroupContent>
                  {group.sections.map((section, sectionIndex) => {
                    const sectionId = `${group.label}-${sectionIndex}`;
                    const collapsed = isSectionCollapsed(sectionId);

                    return (
                      <React.Fragment key={sectionId}>
                        {/* Render section header for reports/setup sections */}
                        {section.label && (
                          <SidebarSectionHeader
                            label={t(section.label)}
                            sectionType={section.type}
                            sectionId={sectionId}
                            isCollapsed={collapsed}
                            onToggle={() => toggleSection(sectionId)}
                          />
                        )}
                        {/* Only render items if not collapsed */}
                        {!collapsed && (
                          <SidebarMenu>
                            {section.items.map((item) => {
                              const Icon = item.icon;
                              const indentClass = getSectionIndentClass(section.type);

                              return (
                                <SidebarMenuItem key={item.to}>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <NavLink
                                        to={item.to}
                                        end={item.to === "/"}
                                        onClick={handleNavigation}
                                        className={({ isActive }) =>
                                          [
                                            "group flex items-center gap-3 rounded-lg border px-3 py-2.5 text-sm font-medium transition-all duration-150",
                                            showLabel ? `justify-start ${indentClass}` : "justify-center px-0",
                                            isActive
                                              ? "border-sidebar-accent/50 bg-sidebar-accent text-sidebar-accent-foreground shadow-sm"
                                              : "border-transparent text-sidebar-foreground/90 hover:border-sidebar-accent/30 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
                                          ].join(" ")
                                        }
                                      >
                                        <Icon className="size-4 shrink-0" />
                                        {showLabel ? (
                                          <span className="flex min-w-0 flex-1 items-center justify-between gap-2">
                                            <span className="truncate">{t(item.label)}</span>
                                            <ChevronRight className="size-3.5 text-sidebar-foreground/50 transition-transform group-hover:translate-x-0.5" />
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
                        )}
                      </React.Fragment>
                    );
                  })}
                </SidebarGroupContent>
              )}
            </SidebarGroup>
          );
        })}
      </SidebarContent>

      <SidebarFooter>
        <div className="space-y-3">
          {showLabel ? (
            <div className="rounded-xl border border-sidebar-border/50 bg-sidebar-accent/30 px-3 py-3">
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-sidebar-muted">
                {t("nav.language")}
              </p>
              <LanguageSwitcher />
            </div>
          ) : null}

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="flex w-full items-center gap-3 rounded-xl border border-sidebar-border/50 bg-sidebar-accent/30 px-3 py-3 text-left transition-colors hover:bg-sidebar-accent/50"
              >
                <Avatar className="size-10 border border-sidebar-border/60">
                  <AvatarFallback className="bg-sidebar-accent/60 text-sidebar-accent-foreground">{getInitials(user?.sub ?? "")}</AvatarFallback>
                </Avatar>
                {showLabel ? (
                  <div className="min-w-0 flex-1 space-y-1">
                    <p className="truncate text-sm font-medium text-sidebar-foreground">{user?.sub ?? t("common.guest")}</p>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline" className="border-sidebar-border/60 bg-transparent text-[10px] text-sidebar-muted">
                        {user?.role ?? t("common.guest")}
                      </Badge>
                      <span className="truncate text-xs text-sidebar-muted/80">{user?.tenant_id ?? t("common.noTenant")}</span>
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