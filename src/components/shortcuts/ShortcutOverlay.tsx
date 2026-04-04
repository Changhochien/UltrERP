import type { RefObject } from "react";

import {
  formatShortcutBinding,
  isMacPlatform,
  type ShortcutDefinition,
} from "../../lib/shortcuts";

interface ShortcutOverlayProps {
  open: boolean;
  globalShortcuts: readonly ShortcutDefinition[];
  screenShortcuts: readonly ShortcutDefinition[];
  onClose: () => void;
  showDesktopBindings: boolean;
  panelRef: RefObject<HTMLDivElement | null>;
}

function ShortcutSection({
  title,
  shortcuts,
  emptyMessage,
  showDesktopBindings,
}: {
  title: string;
  shortcuts: readonly ShortcutDefinition[];
  emptyMessage: string;
  showDesktopBindings: boolean;
}) {
  const isMac = isMacPlatform();
  const sectionId = `shortcut-section-${title.toLowerCase().replace(/\s+/g, "-")}`;

  return (
    <section className="shortcut-overlay-section" aria-labelledby={sectionId}>
      <div className="shortcut-overlay-section-header">
        <h2 id={sectionId}>{title}</h2>
      </div>
      {shortcuts.length === 0 ? (
        <p className="shortcut-overlay-empty">{emptyMessage}</p>
      ) : (
        <ul className="shortcut-overlay-list">
          {shortcuts.map((shortcut) => (
            <li className="shortcut-overlay-item" key={shortcut.id}>
              <div>
                <strong>{shortcut.label}</strong>
                <p>{shortcut.description}</p>
              </div>
              <div className="shortcut-overlay-bindings">
                {shortcut.appBindings.map((binding) => (
                  <span className="shortcut-overlay-binding" key={`${shortcut.id}-${binding.raw}`}>
                    {formatShortcutBinding(binding, isMac)}
                  </span>
                ))}
                {showDesktopBindings
                  ? shortcut.desktopGlobalBindings.map((binding) => (
                      <span
                        className="shortcut-overlay-binding shortcut-overlay-binding-desktop"
                        key={`${shortcut.id}-desktop-${binding.raw}`}
                      >
                        Desktop {formatShortcutBinding(binding, isMac)}
                      </span>
                    ))
                  : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function ShortcutOverlay({
  open,
  globalShortcuts,
  screenShortcuts,
  onClose,
  showDesktopBindings,
  panelRef,
}: ShortcutOverlayProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="shortcut-overlay-backdrop" onClick={onClose}>
      <div
        aria-label="Keyboard shortcuts"
        aria-modal="true"
        className="shortcut-overlay-panel"
        onClick={(event) => event.stopPropagation()}
        ref={panelRef}
        role="dialog"
        tabIndex={-1}
      >
        <div className="shortcut-overlay-head">
          <div>
            <p className="eyebrow">Power user workflow</p>
            <h1>Keyboard shortcuts</h1>
          </div>
          <button type="button" onClick={onClose}>
            Close
          </button>
        </div>

        <ShortcutSection
          emptyMessage="No global shortcuts are available for your current role."
          shortcuts={globalShortcuts}
          showDesktopBindings={showDesktopBindings}
          title="Global"
        />
        <ShortcutSection
          emptyMessage="No screen-specific shortcuts are available on this page."
          shortcuts={screenShortcuts}
          showDesktopBindings={showDesktopBindings}
          title="On this screen"
        />
      </div>
    </div>
  );
}