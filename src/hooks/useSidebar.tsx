import * as React from "react";
import { useIsMobile } from "./useIsMobile";
import { TooltipProvider } from "../components/ui/tooltip";

const SIDEBAR_STORAGE_KEY = "ultrerp.sidebar.open";

interface SidebarContextValue {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  openMobile: boolean;
  setOpenMobile: React.Dispatch<React.SetStateAction<boolean>>;
  isMobile: boolean;
  toggleSidebar: () => void;
}

const SidebarContext = React.createContext<SidebarContextValue | null>(null);

function useSidebar() {
  const context = React.useContext(SidebarContext);

  if (!context) {
    throw new Error("useSidebar must be used within a SidebarProvider.");
  }

  return context;
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

  React.useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(open));
  }, [open]);

  const toggleSidebar = React.useCallback(() => {
    if (isMobile) {
      setOpenMobile((current) => !current);
      return;
    }

    setOpen((current) => !current);
  }, [isMobile]);

  const value = React.useMemo(
    () => ({ open, setOpen, openMobile, setOpenMobile, isMobile, toggleSidebar }),
    [isMobile, open, openMobile, toggleSidebar],
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
