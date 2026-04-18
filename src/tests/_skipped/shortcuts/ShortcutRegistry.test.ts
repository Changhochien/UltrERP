import { describe, expect, it } from "vitest";

import {
  buildShortcutRegistry,
  isEditableTarget,
  normalizeShortcutBinding,
  parseShortcutBinding,
  SHORTCUT_REGISTRY,
  toTauriShortcut,
  type ShortcutSeed,
} from "../../lib/shortcuts";
import { HOME_ROUTE } from "../../lib/routes";

const baseShortcut: ShortcutSeed = {
  id: "base-shortcut",
  label: "Base shortcut",
  description: "Base shortcut for registry validation tests.",
  category: "Test",
  scope: "global",
  appBindings: ["g d"],
  target: { type: "route", to: HOME_ROUTE },
};

describe("shortcut registry", () => {
  it("normalizes modifier ordering", () => {
    expect(normalizeShortcutBinding("shift+ctrl+/ ")).toBe("mod+shift+/");
  });

  it("rejects duplicate bindings at registry build time", () => {
    expect(() =>
      buildShortcutRegistry([
        baseShortcut,
        {
          ...baseShortcut,
          id: "duplicate-shortcut",
          label: "Duplicate shortcut",
        },
      ]),
    ).toThrow(/binding conflict/i);
  });

  it("rejects prefix conflicts at registry build time", () => {
    expect(() =>
      buildShortcutRegistry([
        {
          ...baseShortcut,
          id: "prefix-a",
          label: "Prefix A",
          appBindings: ["g"],
        },
        {
          ...baseShortcut,
          id: "prefix-b",
          label: "Prefix B",
          appBindings: ["g d"],
        },
      ]),
    ).toThrow(/prefix conflict/i);
  });

  it("rejects reverse-order prefix conflicts at registry build time", () => {
    expect(() =>
      buildShortcutRegistry([
        {
          ...baseShortcut,
          id: "prefix-b",
          label: "Prefix B",
          appBindings: ["g d"],
        },
        {
          ...baseShortcut,
          id: "prefix-a",
          label: "Prefix A",
          appBindings: ["g"],
        },
      ]),
    ).toThrow(/prefix conflict/i);
  });

  it("keeps the shipped registry normalized", () => {
    for (const shortcut of SHORTCUT_REGISTRY) {
      for (const binding of shortcut.appBindings) {
        expect(binding.steps.join(" ")).toBe(normalizeShortcutBinding(binding.raw));
      }
    }
  });

  it("converts desktop bindings to Tauri shortcut syntax", () => {
    expect(
      toTauriShortcut({ raw: "mod+/", steps: parseShortcutBinding("mod+/") }),
    ).toBe("CommandOrControl+/");
  });

  it("treats plaintext-only editors as editable targets", () => {
    const editor = document.createElement("div");
    editor.setAttribute("contenteditable", "plaintext-only");
    document.body.append(editor);

    try {
      expect(isEditableTarget(editor)).toBe(true);
    } finally {
      editor.remove();
    }
  });

  it("treats selects as editable targets", () => {
    const select = document.createElement("select");
    document.body.append(select);

    try {
      expect(isEditableTarget(select)).toBe(true);
    } finally {
      select.remove();
    }
  });
});