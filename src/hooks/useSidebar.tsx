import * as React from "react";
import { useIsMobile } from "./useIsMobile";
import { TooltipProvider } from "../components/ui/tooltip";

const SIDEBAR_STORAGE_KEY = "ultrerp.sidebar.open";
const COLLAPSED_SECTIONS_KEY = "ultrerp.sidebar.collapsed-sections";
const COLLAPSED_GROUPS_KEY = "ultrerp.sidebar.collapsed-groups";

interface SidebarContextValue {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  openMobile: boolean;
  setOpenMobile: React.Dispatch<React.SetStateAction<boolean>>;
  isMobile: boolean;
  toggleSidebar: () => void;
  collapsedSections: Set<string>;
  toggleSection: (sectionId: string) => void;
  isSectionCollapsed: (sectionId: string) => boolean;
  collapsedGroups: Set<string>;
  toggleGroup: (groupId: string) => void;
  isGroupCollapsed: (groupId: string) => boolean;
}

const SidebarContext = React.createContext<SidebarContextValue | null>(null);

function useSidebar() {
  const context = React.useContext(SidebarContext);

  if (!context) {
    throw new Error("useSidebar must be used within a SidebarProvider.");
  }

  return context;
}

// Generic localStorage helpers with error handling for SSR compatibility
function createLocalStorageSet<T>(key: string) {
  return (value: T): void => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // Silently fail (quota exceeded, private browsing, etc.)
    }
  };
}

function createLocalStorageGet<T>(key: string, defaultValue: T) {
  return (): T => {
    if (typeof window === "undefined") return defaultValue;
    try {
      const stored = window.localStorage.getItem(key);
      if (stored == null) return defaultValue;
      const parsed = JSON.parse(stored) as T;
      return Array.isArray(parsed) ? parsed : defaultValue;
    } catch {
      return defaultValue;
    }
  };
}

// Specific localStorage helpers for sidebar state
const getStoredCollapsedSections = createLocalStorageGet<string[]>(COLLAPSED_SECTIONS_KEY, []);
const setStoredCollapsedSections = createLocalStorageSet<string[]>(COLLAPSED_SECTIONS_KEY);
const getStoredCollapsedGroups = createLocalStorageGet<string[]>(COLLAPSED_GROUPS_KEY, []);
const setStoredCollapsedGroups = createLocalStorageSet<string[]>(COLLAPSED_GROUPS_KEY);

function SidebarProvider({ defaultOpen = true, children }: { defaultOpen?: boolean; children: React.ReactNode }) {
  const isMobile = useIsMobile();
  const [openMobile, setOpenMobile] = React.useState(false);
  const [open, setOpen] = React.useState(() => {
    if (typeof window === "undefined") {
      return defaultOpen;
    }

    const stored = window.localStorage.getItem(SIDEBAR_STORAGE_KEY);
    return stored == null ? defaultOpen : stored === "true";
  });

  // Section collapse state (stored as array, converted to Set for runtime)
  const [collapsedSections, setCollapsedSections] = React.useState<Set<string>>(() => new Set(getStoredCollapsedSections()));

  // Group collapse state (stored as array, converted to Set for runtime)
  const [collapsedGroups, setCollapsedGroups] = React.useState<Set<string>>(() => new Set(getStoredCollapsedGroups()));

  // Persist open state
  React.useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(open));
  }, [open]);

  // Persist collapsed sections (convert Set to array for storage)
  React.useEffect(() => {
    setStoredCollapsedSections(Array.from(collapsedSections));
  }, [collapsedSections]);

  // Persist collapsed groups (convert Set to array for storage)
  React.useEffect(() => {
    setStoredCollapsedGroups(Array.from(collapsedGroups));
  }, [collapsedGroups]);

  const toggleSidebar = React.useCallback(() => {
    if (isMobile) {
      setOpenMobile((current) => !current);
      return;
    }

    setOpen((current) => !current);
  }, [isMobile]);

  const toggleSection = React.useCallback((sectionId: string) => {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }
      return next;
    });
  }, []);

  const isSectionCollapsed = React.useCallback(
    (sectionId: string) => collapsedSections.has(sectionId),
    [collapsedSections],
  );

  const toggleGroup = React.useCallback((groupId: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  }, []);

  const isGroupCollapsed = React.useCallback(
    (groupId: string) => collapsedGroups.has(groupId),
    [collapsedGroups],
  );

  const value = React.useMemo(
    () => ({
      open,
      setOpen,
      openMobile,
      setOpenMobile,
      isMobile,
      toggleSidebar,
      collapsedSections,
      toggleSection,
      isSectionCollapsed,
      collapsedGroups,
      toggleGroup,
      isGroupCollapsed,
    }),
    [isMobile, open, openMobile, toggleSidebar, collapsedSections, toggleSection, isSectionCollapsed, collapsedGroups, toggleGroup, isGroupCollapsed],
  );

  return (
    <SidebarContext.Provider value={value}>
      <TooltipProvider delayDuration={0}>
        <div className="min-h-screen bg-background text-foreground">{children}</div>
      </TooltipProvider>
    </SidebarContext.Provider>
  );
}

export { useSidebar, SidebarProvider };
