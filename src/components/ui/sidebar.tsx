import * as React from "react";
import { ChevronDown, PanelLeftClose, PanelLeftOpen } from "lucide-react";

import { useSidebar, SidebarProvider } from "../../hooks/useSidebar";
import { cn } from "../../lib/utils";
import type { NavigationSectionType } from "../../lib/navigation";
import { Button } from "./button";

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

function Sidebar({ className, children, ...props }: SidebarProps) {
  const { isMobile, open, openMobile, setOpenMobile } = useSidebar();

  if (isMobile) {
    return (
      <>
        {openMobile ? (
          <button
            type="button"
            aria-label="Close navigation"
            className="fixed inset-0 z-20 bg-[color:var(--overlay-scrim)] backdrop-blur-sm"
            onClick={() => setOpenMobile(false)}
          />
        ) : null}
        <aside
          data-state={openMobile ? "expanded" : "collapsed"}
          className={cn(
            "fixed inset-y-0 left-0 z-30 flex h-screen border-r border-sidebar-border/70 bg-sidebar text-sidebar-foreground shadow-[0_0_0_1px_rgba(148,163,184,0.08)] transition-[width] duration-200 ease-out",
            openMobile ? "w-72" : "w-20",
            className,
          )}
          {...props}
        >
          <div className="flex h-full w-full flex-col overflow-hidden">{children}</div>
        </aside>
      </>
    );
  }

  return (
    <aside
      data-state={open ? "expanded" : "collapsed"}
      className={cn(
        "fixed inset-y-0 left-0 z-30 hidden h-screen border-r border-sidebar-border/70 bg-sidebar text-sidebar-foreground shadow-[0_0_0_1px_rgba(148,163,184,0.08)] transition-[width] duration-200 ease-out sm:flex",
        open ? "w-72" : "w-20",
        className,
      )}
      {...props}
    >
      <div className="flex h-full w-full flex-col">{children}</div>
    </aside>
  );
}

const SidebarHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("border-b border-sidebar-border/70 px-4 py-4", className)} {...props} />,
);
SidebarHeader.displayName = "SidebarHeader";

const SidebarContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("flex-1 overflow-y-auto px-3 py-4", className)} {...props} />,
);
SidebarContent.displayName = "SidebarContent";

const SidebarFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("mt-auto border-t border-sidebar-border/70 px-3 py-4", className)} {...props} />,
);
SidebarFooter.displayName = "SidebarFooter";

const SidebarGroup = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("mb-4", className)} {...props} />,
);
SidebarGroup.displayName = "SidebarGroup";

const SidebarGroupLabel = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => {
    const { open, openMobile, isMobile } = useSidebar();
    const showLabel = isMobile ? openMobile : open;

    return (
      <p
        ref={ref}
        className={cn(
          "mb-2 px-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-sidebar-foreground/45",
          !showLabel && "sr-only",
          className,
        )}
        {...props}
      />
    );
  },
);
SidebarGroupLabel.displayName = "SidebarGroupLabel";

const SidebarGroupContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("space-y-1", className)} {...props} />,
);
SidebarGroupContent.displayName = "SidebarGroupContent";

// Section header component for reports/setup sections
interface SidebarSectionHeaderProps extends React.HTMLAttributes<HTMLButtonElement> {
  label: string;
  sectionType: NavigationSectionType;
  sectionId: string;
  isCollapsed?: boolean;
  onToggle?: () => void;
}

const SidebarSectionHeader = React.forwardRef<HTMLButtonElement, SidebarSectionHeaderProps>(
  ({ label, sectionType, sectionId, isCollapsed = false, onToggle, className, ...props }, ref) => {
    const { open, openMobile, isMobile } = useSidebar();
    const showLabel = isMobile ? openMobile : open;

    // Don't render section headers in collapsed sidebar mode
    if (!showLabel) return null;

    const handleClick = () => {
      onToggle?.();
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onToggle?.();
      }
    };

    return (
      <button
        ref={ref}
        type="button"
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        aria-expanded={!isCollapsed}
        aria-controls={`section-${sectionId}`}
        className={cn(
          "mb-1 mt-3 flex w-full items-center justify-between px-2 py-1.5 text-left text-[11px] font-semibold uppercase tracking-[0.24em] transition-colors",
          sectionType === 'reports' && "text-sidebar-foreground/50",
          sectionType === 'setup' && "text-sidebar-foreground/40",
          "cursor-pointer rounded hover:bg-sidebar-accent/40",
          className,
        )}
        {...props}
      >
        <span>{label}</span>
        <ChevronDown
          className={cn(
            "size-3 shrink-0 text-sidebar-foreground/40 transition-transform duration-200",
            isCollapsed ? "-rotate-90" : "rotate-0",
          )}
        />
      </button>
    );
  },
);
SidebarSectionHeader.displayName = "SidebarSectionHeader";

const SidebarMenu = React.forwardRef<HTMLUListElement, React.HTMLAttributes<HTMLUListElement>>(
  ({ className, ...props }, ref) => <ul ref={ref} className={cn("space-y-1", className)} {...props} />,
);
SidebarMenu.displayName = "SidebarMenu";

const SidebarMenuItem = React.forwardRef<HTMLLIElement, React.HTMLAttributes<HTMLLIElement>>(
  ({ className, ...props }, ref) => <li ref={ref} className={cn("list-none", className)} {...props} />,
);
SidebarMenuItem.displayName = "SidebarMenuItem";

const SidebarInset = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => {
    const { isMobile, open } = useSidebar();

    return (
      <div
        ref={ref}
        className={cn(
          "min-h-screen transition-[padding-left] duration-200 ease-out",
          isMobile ? "pl-20" : "sm:pl-20",
          open && "sm:pl-72",
          className,
        )}
        {...props}
      />
    );
  },
);
SidebarInset.displayName = "SidebarInset";

function SidebarTrigger({ className, ...props }: React.ComponentProps<typeof Button>) {
  const { isMobile, open, openMobile, toggleSidebar } = useSidebar();
  const isExpanded = isMobile ? openMobile : open;
  const Icon = isExpanded ? PanelLeftClose : PanelLeftOpen;

  return (
    <Button
      variant="outline"
      size="icon"
      className={cn("rounded-xl", className)}
      onClick={toggleSidebar}
      aria-expanded={isExpanded}
      {...props}
    >
      <Icon className="size-4" />
      <span className="sr-only">Toggle navigation</span>
    </Button>
  );
}

export {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuItem,
  SidebarProvider,
  SidebarSectionHeader,
  SidebarTrigger,
  useSidebar,
};
