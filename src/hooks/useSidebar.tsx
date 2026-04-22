import * as React from "react";
import { useIsMobile } from "./useIsMobile";
import { TooltipProvider } from "../components/ui/tooltip";

const SIDEBAR_STORAGE_KEY = "ultrerp.sidebar.open";
const COLLAPSED_SECTIONS_KEY = "ultrerp.sidebar.collapsed-sections";

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
}

const SidebarContext = React.createContext<SidebarContextValue | null>(null);

function useSidebar() {
  const context = React.useContext(SidebarContext);

  if (!context) {
    throw new Error("useSidebar must be used within a SidebarProvider.");
  }

  return context;
}

// Helper to safely get/set localStorage with error handling
function getStoredCollapsedSections(): Set<string> {
  if (typeof window === "undefined") {
    return new Set();
  }

  try {
    const stored = window.localStorage.getItem(COLLAPSED_SECTIONS_KEY);
    if (stored == null) {
      return new Set();
    }
    const parsed = JSON.parse(stored);
    if (Array.isArray(parsed)) {
      return new Set(parsed);
    }
    return new Set();
  } catch {
    // Handle malformed JSON or other localStorage errors
    return new Set();
  }
}

function setStoredCollapsedSections(sections: Set<string>) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(COLLAPSED_SECTIONS_KEY, JSON.stringify(Array.from(sections)));
  } catch {
    // Handle localStorage errors (quota exceeded, private browsing, etc.)
    // Silently fail - state will still work in memory
  }
}

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

  // Section collapse state
  const [collapsedSections, setCollapsedSections] = React.useState<Set<string>>(() => getStoredCollapsedSections());

  // Persist open state
  React.useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(open));
  }, [open]);

  // Persist collapsed sections
  React.useEffect(() => {
    setStoredCollapsedSections(collapsedSections);
  }, [collapsedSections]);

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
    }),
    [isMobile, open, openMobile, toggleSidebar, collapsedSections, toggleSection, isSectionCollapsed],
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
