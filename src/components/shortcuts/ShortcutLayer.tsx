import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { usePermissions } from "../../hooks/usePermissions";
import {
  eventToShortcutStep,
  getAvailableShortcuts,
  isEditableTarget,
  resolveShortcutProgress,
  SHORTCUT_REGISTRY,
  type ShortcutDefinition,
} from "../../lib/shortcuts";
import {
  isDesktopShell,
  registerDesktopShortcuts,
} from "../../lib/desktop/globalShortcuts";
import { ShortcutOverlay } from "./ShortcutOverlay";

const SEQUENCE_TIMEOUT_MS = 1200;
const OVERLAY_FOCUSABLE_SELECTOR = [
  "button:not([disabled])",
  "a[href]",
  'input:not([disabled]):not([type="hidden"])',
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"]):not([disabled])',
].join(",");
const DESKTOP_SHORTCUTS = SHORTCUT_REGISTRY.flatMap((shortcut) =>
  shortcut.desktopGlobalBindings.map((binding) => ({
    binding,
    id: shortcut.id,
  })),
);

function getOverlayFocusableElements(panel: HTMLElement | null): HTMLElement[] {
  if (!panel) {
    return [];
  }

  return Array.from(panel.querySelectorAll<HTMLElement>(OVERLAY_FOCUSABLE_SELECTOR)).filter(
    (element) => !element.hasAttribute("disabled") && !element.getAttribute("aria-hidden"),
  );
}

export function ShortcutLayer() {
  const location = useLocation();
  const navigate = useNavigate();
  const { canAccess, canWrite } = usePermissions();
  const [isOverlayOpen, setOverlayOpen] = useState(false);
  const [focusSequence, setFocusSequence] = useState(0);
  const [pendingHint, setPendingHint] = useState("");
  const pendingSequenceRef = useRef<string[]>([]);
  const sequenceTimerRef = useRef<number | null>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const overlayPanelRef = useRef<HTMLDivElement | null>(null);
  const availableShortcutsRef = useRef<readonly ShortcutDefinition[]>([]);

  const availableShortcuts = useMemo(
    () => getAvailableShortcuts({ path: location.pathname, canAccess, canWrite }),
    [canAccess, canWrite, location.pathname],
  );
  const globalShortcuts = useMemo(
    () => availableShortcuts.filter((shortcut) => shortcut.scope === "global"),
    [availableShortcuts],
  );
  const screenShortcuts = useMemo(
    () => availableShortcuts.filter((shortcut) => shortcut.scope === "screen"),
    [availableShortcuts],
  );

  useEffect(() => {
    availableShortcutsRef.current = availableShortcuts;
  }, [availableShortcuts]);

  const clearPendingSequence = useEffectEvent(() => {
    pendingSequenceRef.current = [];
    setPendingHint("");
    if (sequenceTimerRef.current !== null) {
      window.clearTimeout(sequenceTimerRef.current);
      sequenceTimerRef.current = null;
    }
  });

  const armPendingSequence = useEffectEvent((steps: string[]) => {
    pendingSequenceRef.current = steps;
    setPendingHint(steps.join(" "));
    if (sequenceTimerRef.current !== null) {
      window.clearTimeout(sequenceTimerRef.current);
    }
    sequenceTimerRef.current = window.setTimeout(() => {
      pendingSequenceRef.current = [];
      setPendingHint("");
      sequenceTimerRef.current = null;
    }, SEQUENCE_TIMEOUT_MS);
  });

  const executeShortcut = useEffectEvent((shortcut: ShortcutDefinition) => {
    clearPendingSequence();

    if (shortcut.target.type === "overlay") {
      setOverlayOpen(true);
      setFocusSequence((value) => value + 1);
      return;
    }

    navigate(shortcut.target.to);
  });

  const trapOverlayFocus = useEffectEvent((event: KeyboardEvent) => {
    const panel = overlayPanelRef.current;
    if (!panel) {
      return;
    }

    const focusableElements = getOverlayFocusableElements(panel);
    if (focusableElements.length === 0) {
      event.preventDefault();
      panel.focus();
      return;
    }

    const activeElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const currentIndex = activeElement ? focusableElements.indexOf(activeElement) : -1;
    const nextIndex = event.shiftKey
      ? currentIndex <= 0
        ? focusableElements.length - 1
        : currentIndex - 1
      : currentIndex === -1 || currentIndex === focusableElements.length - 1
        ? 0
        : currentIndex + 1;

    event.preventDefault();
    focusableElements[nextIndex]?.focus();
  });

  const resolveAndExecute = useEffectEvent((step: string, event: KeyboardEvent) => {
    const resolution = resolveShortcutProgress(
      availableShortcuts,
      pendingSequenceRef.current,
      step,
    );

    if (resolution.exactMatches.length === 1 && resolution.prefixMatches.length === 0) {
      event.preventDefault();
      executeShortcut(resolution.exactMatches[0].shortcut);
      return true;
    }

    if (resolution.prefixMatches.length > 0) {
      event.preventDefault();
      armPendingSequence(resolution.attemptedSteps);
      return true;
    }

    return false;
  });

  const handleKeyDown = useEffectEvent((event: KeyboardEvent) => {
    const step = eventToShortcutStep(event);

    if (isOverlayOpen) {
      if (event.key === "Tab") {
        trapOverlayFocus(event);
        return;
      }

      if (step === "escape") {
        event.preventDefault();
        setOverlayOpen(false);
        clearPendingSequence();
      }
      return;
    }

    if (!step) {
      return;
    }

    if (isEditableTarget(event.target)) {
      clearPendingSequence();
      return;
    }

    if (resolveAndExecute(step, event)) {
      return;
    }

    if (pendingSequenceRef.current.length > 0) {
      clearPendingSequence();
      void resolveAndExecute(step, event);
    }
  });

  useEffect(() => {
    const listener = (event: KeyboardEvent) => handleKeyDown(event);
    window.addEventListener("keydown", listener);
    return () => {
      window.removeEventListener("keydown", listener);
      pendingSequenceRef.current = [];
      setPendingHint("");
      if (sequenceTimerRef.current !== null) {
        window.clearTimeout(sequenceTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!isOverlayOpen) {
      if (previousFocusRef.current) {
        previousFocusRef.current.focus();
        previousFocusRef.current = null;
      }
      return;
    }

    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;

    const nextFrame = window.requestAnimationFrame(() => {
      const panel = overlayPanelRef.current;
      const focusableElements = getOverlayFocusableElements(panel);
      (focusableElements[0] ?? panel)?.focus();
    });

    return () => {
      window.cancelAnimationFrame(nextFrame);
    };
  }, [focusSequence, isOverlayOpen]);

  useEffect(() => {
    let isActive = true;
    let cleanupDesktopShortcuts: (() => Promise<void>) | null = null;

    void registerDesktopShortcuts(DESKTOP_SHORTCUTS, (shortcutId) => {
      if (isEditableTarget(document.activeElement)) {
        return;
      }

      const shortcut = availableShortcutsRef.current.find((candidate) => candidate.id === shortcutId);
      if (!shortcut) {
        return;
      }
      executeShortcut(shortcut);
    }, () => isActive).then((cleanup) => {
      if (!isActive) {
        void cleanup();
        return;
      }
      cleanupDesktopShortcuts = cleanup;
    });

    return () => {
      isActive = false;
      if (cleanupDesktopShortcuts) {
        void cleanupDesktopShortcuts();
      }
    };
  }, [executeShortcut]);

  return (
    <>
      {pendingHint ? <span className="shortcut-sequence-status">Sequence: {pendingHint}</span> : null}
      <ShortcutOverlay
        globalShortcuts={globalShortcuts}
        onClose={() => setOverlayOpen(false)}
        open={isOverlayOpen}
        panelRef={overlayPanelRef}
        screenShortcuts={screenShortcuts}
        showDesktopBindings={isDesktopShell()}
      />
    </>
  );
}