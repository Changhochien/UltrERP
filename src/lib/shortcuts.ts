import type { AppFeature } from "../hooks/usePermissions";
import {
  ADMIN_ROUTE,
  CUSTOMER_CREATE_ROUTE,
  CUSTOMERS_ROUTE,
  HOME_ROUTE,
  INVENTORY_ROUTE,
  INVOICES_ROUTE,
  INVOICE_CREATE_ROUTE,
  ORDER_CREATE_ROUTE,
  ORDERS_ROUTE,
  PAYMENTS_ROUTE,
  PURCHASES_ROUTE,
  type AppRoute,
} from "./routes";

export type ShortcutScope = "global" | "screen";

export interface ShortcutAccessContext {
  path: string;
  canAccess: (feature: AppFeature) => boolean;
  canWrite: (feature: AppFeature) => boolean;
}

export interface PreparedShortcutBinding {
  raw: string;
  steps: string[];
}

export interface ShortcutDefinition {
  id: string;
  label: string;
  description: string;
  category: string;
  scope: ShortcutScope;
  appBindings: PreparedShortcutBinding[];
  desktopGlobalBindings: PreparedShortcutBinding[];
  target:
    | { type: "overlay"; action: "open" }
    | { type: "route"; to: AppRoute };
  requiredFeature?: AppFeature;
  requiresWrite?: boolean;
  routeMatches?: readonly string[];
}

export interface ShortcutSeed {
  id: string;
  label: string;
  description: string;
  category: string;
  scope: ShortcutScope;
  appBindings: readonly string[];
  desktopGlobalBindings?: readonly string[];
  target:
    | { type: "overlay"; action: "open" }
    | { type: "route"; to: AppRoute };
  requiredFeature?: AppFeature;
  requiresWrite?: boolean;
  routeMatches?: readonly string[];
}

const MODIFIER_ORDER = ["mod", "alt", "shift"] as const;
const EDITABLE_SELECTOR = [
  'input:not([type="button"]):not([type="checkbox"]):not([type="file"]):not([type="hidden"]):not([type="image"]):not([type="radio"]):not([type="range"]):not([type="reset"]):not([type="submit"])',
  "textarea",
  "select",
  '[contenteditable]:not([contenteditable="false"])',
  '[role="textbox"]',
  '[role="combobox"]',
].join(",");

const SHORTCUT_SEEDS: readonly ShortcutSeed[] = [
  {
    id: "open-shortcuts",
    label: "Open shortcuts",
    description: "Show the keyboard shortcut overlay.",
    category: "Global",
    scope: "global",
    appBindings: ["?", "mod+/"],
    desktopGlobalBindings: ["mod+/"],
    target: { type: "overlay", action: "open" },
  },
  {
    id: "go-dashboard",
    label: "Go to dashboard",
    description: "Jump to the dashboard.",
    category: "Navigation",
    scope: "global",
    appBindings: ["g d"],
    target: { type: "route", to: HOME_ROUTE },
    requiredFeature: "dashboard",
  },
  {
    id: "go-inventory",
    label: "Go to inventory",
    description: "Jump to inventory operations.",
    category: "Navigation",
    scope: "global",
    appBindings: ["g i"],
    target: { type: "route", to: INVENTORY_ROUTE },
    requiredFeature: "inventory",
  },
  {
    id: "go-customers",
    label: "Go to customers",
    description: "Jump to customer management.",
    category: "Navigation",
    scope: "global",
    appBindings: ["g c"],
    target: { type: "route", to: CUSTOMERS_ROUTE },
    requiredFeature: "customers",
  },
  {
    id: "go-invoices",
    label: "Go to invoices",
    description: "Jump to the invoice workspace.",
    category: "Navigation",
    scope: "global",
    appBindings: ["g v"],
    target: { type: "route", to: INVOICES_ROUTE },
    requiredFeature: "invoices",
  },
  {
    id: "go-orders",
    label: "Go to orders",
    description: "Jump to the orders workspace.",
    category: "Navigation",
    scope: "global",
    appBindings: ["g o"],
    target: { type: "route", to: ORDERS_ROUTE },
    requiredFeature: "orders",
  },
  {
    id: "go-payments",
    label: "Go to payments",
    description: "Jump to payment operations.",
    category: "Navigation",
    scope: "global",
    appBindings: ["g p"],
    target: { type: "route", to: PAYMENTS_ROUTE },
    requiredFeature: "payments",
  },
  {
    id: "go-purchases",
    label: "Go to purchases",
    description: "Jump to imported supplier invoices.",
    category: "Navigation",
    scope: "global",
    appBindings: ["g u"],
    target: { type: "route", to: PURCHASES_ROUTE },
    requiredFeature: "purchases",
  },
  {
    id: "go-admin",
    label: "Go to admin",
    description: "Jump to administrative controls.",
    category: "Navigation",
    scope: "global",
    appBindings: ["g a"],
    target: { type: "route", to: ADMIN_ROUTE },
    requiredFeature: "admin",
  },
  {
    id: "new-customer",
    label: "New customer",
    description: "Open the create customer flow.",
    category: "Customers",
    scope: "screen",
    appBindings: ["c n"],
    target: { type: "route", to: CUSTOMER_CREATE_ROUTE },
    requiredFeature: "customers",
    requiresWrite: true,
    routeMatches: [CUSTOMERS_ROUTE],
  },
  {
    id: "new-invoice",
    label: "New invoice",
    description: "Open the create invoice flow.",
    category: "Invoices",
    scope: "screen",
    appBindings: ["v n"],
    target: { type: "route", to: INVOICE_CREATE_ROUTE },
    requiredFeature: "invoices",
    requiresWrite: true,
    routeMatches: [INVOICES_ROUTE],
  },
  {
    id: "new-order",
    label: "New order",
    description: "Open the create order flow.",
    category: "Orders",
    scope: "screen",
    appBindings: ["o n"],
    target: { type: "route", to: ORDER_CREATE_ROUTE },
    requiredFeature: "orders",
    requiresWrite: true,
    routeMatches: [ORDERS_ROUTE],
  },
] as const;

export const SHORTCUT_REGISTRY: readonly ShortcutDefinition[] = buildShortcutRegistry(
  SHORTCUT_SEEDS,
);

export function buildShortcutRegistry(
  shortcuts: readonly ShortcutSeed[],
): readonly ShortcutDefinition[] {
  const prepared = shortcuts.map((shortcut) => ({
    ...shortcut,
    appBindings: shortcut.appBindings.map((binding) => ({
      raw: binding,
      steps: parseShortcutBinding(binding),
    })),
    desktopGlobalBindings: (shortcut.desktopGlobalBindings ?? []).map((binding) => ({
      raw: binding,
      steps: parseShortcutBinding(binding),
    })),
  }));

  validateShortcutRegistry(prepared);
  return prepared;
}

export function getAvailableShortcuts(
  context: ShortcutAccessContext,
): ShortcutDefinition[] {
  return SHORTCUT_REGISTRY.filter((shortcut) => isShortcutAvailable(shortcut, context));
}

function isShortcutAvailable(
  shortcut: ShortcutDefinition,
  context: ShortcutAccessContext,
): boolean {
  if (shortcut.requiredFeature && !context.canAccess(shortcut.requiredFeature)) {
    return false;
  }

  if (
    shortcut.requiredFeature &&
    shortcut.requiresWrite &&
    !context.canWrite(shortcut.requiredFeature)
  ) {
    return false;
  }

  if (
    shortcut.scope === "screen" &&
    shortcut.routeMatches &&
    !shortcut.routeMatches.includes(context.path)
  ) {
    return false;
  }

  return true;
}

export function normalizeShortcutBinding(binding: string): string {
  return parseShortcutBinding(binding).join(" ");
}

export function parseShortcutBinding(binding: string): string[] {
  const trimmed = binding.trim();
  if (!trimmed) {
    throw new Error("Shortcut bindings cannot be empty.");
  }

  return trimmed
    .split(/\s+/)
    .filter(Boolean)
    .map(normalizeShortcutStep);
}

function normalizeShortcutStep(step: string): string {
  const raw = step.trim().toLowerCase();
  if (!raw) {
    throw new Error("Shortcut steps cannot be empty.");
  }

  if (raw === "?") {
    return "?";
  }

  const tokens = raw.split("+").map((token) => token.trim()).filter(Boolean);
  const modifiers = new Set<string>();
  let keyToken: string | null = null;

  for (const token of tokens) {
    const normalizedModifier = normalizeModifierToken(token);
    if (normalizedModifier) {
      modifiers.add(normalizedModifier);
      continue;
    }

    if (keyToken) {
      throw new Error(`Shortcut step "${step}" has multiple keys.`);
    }
    keyToken = normalizeKeyToken(token);
  }

  if (!keyToken) {
    throw new Error(`Shortcut step "${step}" is missing a key.`);
  }

  const orderedModifiers = MODIFIER_ORDER.filter((modifier) => modifiers.has(modifier));
  return [...orderedModifiers, keyToken].join("+");
}

function normalizeModifierToken(token: string): string | null {
  switch (token) {
    case "commandorcontrol":
    case "cmdorctrl":
    case "cmd":
    case "command":
    case "control":
    case "ctrl":
    case "meta":
    case "mod":
      return "mod";
    case "alt":
    case "option":
      return "alt";
    case "shift":
      return "shift";
    default:
      return null;
  }
}

function normalizeKeyToken(token: string): string {
  switch (token) {
    case "slash":
      return "/";
    case "esc":
      return "escape";
    case "spacebar":
      return "space";
    default:
      return token;
  }
}

function validateShortcutRegistry(shortcuts: readonly ShortcutDefinition[]): void {
  const bindings = new Map<string, string>();

  for (const shortcut of shortcuts) {
    for (const binding of shortcut.appBindings) {
      const key = `app:${binding.steps.join(" ")}`;
      assertUniqueBinding(bindings, key, shortcut.id);
      assertNoPrefixConflicts(bindings, `app:`, binding.steps, shortcut.id);
    }

    for (const binding of shortcut.desktopGlobalBindings) {
      if (binding.steps.length !== 1) {
        throw new Error(
          `Desktop global shortcut "${binding.raw}" for ${shortcut.id} must be a single-step chord.`,
        );
      }
      const key = `desktop:${binding.steps.join(" ")}`;
      assertUniqueBinding(bindings, key, shortcut.id);
    }
  }
}

function assertUniqueBinding(
  bindings: Map<string, string>,
  key: string,
  shortcutId: string,
): void {
  const existing = bindings.get(key);
  if (existing) {
    throw new Error(
      `Shortcut binding conflict between ${existing} and ${shortcutId} for ${key}.`,
    );
  }
  bindings.set(key, shortcutId);
}

function assertNoPrefixConflicts(
  bindings: Map<string, string>,
  namespace: string,
  steps: string[],
  shortcutId: string,
): void {
  const fullBinding = `${namespace}${steps.join(" ")}`;

  for (let index = 1; index < steps.length; index += 1) {
    const prefix = `${namespace}${steps.slice(0, index).join(" ")}`;
    const existing = bindings.get(prefix);
    if (existing) {
      throw new Error(
        `Shortcut binding prefix conflict between ${existing} and ${shortcutId} for ${prefix}.`,
      );
    }
  }

  for (const [existingBinding, existingShortcutId] of bindings.entries()) {
    if (!existingBinding.startsWith(namespace) || existingBinding === fullBinding) {
      continue;
    }

    const existingSteps = existingBinding.slice(namespace.length).split(" ");
    if (existingSteps.length <= steps.length) {
      continue;
    }

    if (steps.every((step, index) => step === existingSteps[index])) {
      throw new Error(
        `Shortcut binding prefix conflict between ${existingShortcutId} and ${shortcutId} for ${fullBinding}.`,
      );
    }
  }
}

export function eventToShortcutStep(event: KeyboardEvent): string | null {
  const key = event.key;

  if (["Control", "Meta", "Alt", "Shift"].includes(key)) {
    return null;
  }

  if (!event.ctrlKey && !event.metaKey && !event.altKey && key === "?") {
    return "?";
  }

  const modifiers: string[] = [];
  if (event.ctrlKey || event.metaKey) {
    modifiers.push("mod");
  }
  if (event.altKey) {
    modifiers.push("alt");
  }
  if (event.shiftKey) {
    modifiers.push("shift");
  }

  const normalizedKey = normalizeEventKey(event);
  if (!normalizedKey) {
    return null;
  }

  return [...modifiers, normalizedKey].join("+");
}

function normalizeEventKey(event: KeyboardEvent): string | null {
  if (event.code === "Slash") {
    return "/";
  }

  if (typeof event.key !== "string" || event.key.length === 0) {
    return null;
  }

  const key = event.key.toLowerCase();
  if (key === " ") {
    return "space";
  }
  if (key === "esc") {
    return "escape";
  }
  if (key.length === 1 || key === "escape") {
    return key;
  }
  return null;
}

export function isEditableTarget(target: EventTarget | null): boolean {
  const element = target instanceof Element ? target : null;
  if (!element) {
    return false;
  }

  if (element instanceof HTMLInputElement && element.type === "hidden") {
    return false;
  }

  if (element instanceof HTMLElement && element.isContentEditable) {
    return true;
  }

  return Boolean(element.closest(EDITABLE_SELECTOR));
}

export function formatShortcutBinding(binding: PreparedShortcutBinding, isMac: boolean): string {
  return binding.steps.map((step) => formatShortcutStep(step, isMac)).join(" then ");
}

function formatShortcutStep(step: string, isMac: boolean): string {
  if (step === "?") {
    return "?";
  }

  const tokens = step.split("+");
  return tokens
    .map((token) => {
      switch (token) {
        case "mod":
          return isMac ? "Cmd" : "Ctrl";
        case "alt":
          return isMac ? "Option" : "Alt";
        case "shift":
          return "Shift";
        case "escape":
          return "Esc";
        case "space":
          return "Space";
        default:
          return token.length === 1 ? token.toUpperCase() : token;
      }
    })
    .join("+");
}

export function isMacPlatform(): boolean {
  if (typeof navigator === "undefined") {
    return false;
  }
  return /mac/i.test(navigator.platform);
}

export function toTauriShortcut(binding: PreparedShortcutBinding): string {
  if (binding.steps.length !== 1) {
    throw new Error(`Desktop shortcut "${binding.raw}" must be a single-step chord.`);
  }

  const step = binding.steps[0];
  if (step === "?") {
    throw new Error("Question-mark shortcuts cannot be registered as desktop global shortcuts.");
  }

  return step
    .split("+")
    .map((token) => {
      switch (token) {
        case "mod":
          return "CommandOrControl";
        case "alt":
          return "Alt";
        case "shift":
          return "Shift";
        case "escape":
          return "Escape";
        case "space":
          return "Space";
        case "/":
          return "/";
        default:
          return token.length === 1 ? token.toUpperCase() : token;
      }
    })
    .join("+");
}

export interface ShortcutBindingMatch {
  shortcut: ShortcutDefinition;
  binding: PreparedShortcutBinding;
}

export interface ShortcutResolution {
  exactMatches: ShortcutBindingMatch[];
  prefixMatches: ShortcutBindingMatch[];
  attemptedSteps: string[];
}

export function resolveShortcutProgress(
  shortcuts: readonly ShortcutDefinition[],
  pendingSteps: readonly string[],
  nextStep: string,
): ShortcutResolution {
  const attemptedSteps = [...pendingSteps, nextStep];
  const exactMatches: ShortcutBindingMatch[] = [];
  const prefixMatches: ShortcutBindingMatch[] = [];

  for (const shortcut of shortcuts) {
    for (const binding of shortcut.appBindings) {
      if (!binding.steps.slice(0, attemptedSteps.length).every((step, index) => step === attemptedSteps[index])) {
        continue;
      }

      const match = { shortcut, binding };
      if (binding.steps.length === attemptedSteps.length) {
        exactMatches.push(match);
      } else {
        prefixMatches.push(match);
      }
    }
  }

  return { exactMatches, prefixMatches, attemptedSteps };
}