import { DEFAULT_NAMESPACE, I18N_NAMESPACES, type I18nNamespace } from './i18n-namespaces';

type TranslationObject = Record<string, unknown>;
type NamespaceResources = Partial<Record<I18nNamespace, TranslationObject>>;

const DOUBLE_BRACE_PATTERN = /\{\{([A-Za-z0-9_]+)\}\}/g;
const LEGACY_COMMON_ROOT_NAMESPACES = I18N_NAMESPACES.filter(
  (namespace) => namespace !== DEFAULT_NAMESPACE && namespace !== 'shell' && namespace !== 'routes',
) as readonly I18nNamespace[];

function isPlainObject(value: unknown): value is TranslationObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function normalizeTranslationNode(node: unknown): unknown {
  if (typeof node === 'string') {
    return node.replace(DOUBLE_BRACE_PATTERN, '{$1}');
  }

  if (Array.isArray(node)) {
    return node.map((value) => normalizeTranslationNode(value));
  }

  if (isPlainObject(node)) {
    return Object.fromEntries(
      Object.entries(node).map(([key, value]) => [key, normalizeTranslationNode(value)]),
    );
  }

  return node;
}

function deepMerge(target: TranslationObject, source: TranslationObject): TranslationObject {
  for (const [key, value] of Object.entries(source)) {
    if (isPlainObject(value) && isPlainObject(target[key])) {
      target[key] = deepMerge({ ...(target[key] as TranslationObject) }, value);
      continue;
    }

    target[key] = value;
  }

  return target;
}

export function normalizeTranslationBundle(bundle: TranslationObject | undefined): TranslationObject {
  if (!bundle) {
    return {};
  }

  return normalizeTranslationNode(bundle) as TranslationObject;
}

export function normalizeNamespaceResources(resources: NamespaceResources): NamespaceResources {
  const normalized: NamespaceResources = {};

  for (const namespace of I18N_NAMESPACES) {
    const bundle = resources[namespace];
    if (bundle) {
      normalized[namespace] = normalizeTranslationBundle(bundle);
    }
  }

  return normalized;
}

export function buildLegacyCommonCompatibilityBundle(resources: NamespaceResources): TranslationObject {
  const compatibilityBundle = normalizeTranslationBundle(resources[DEFAULT_NAMESPACE]);
  const shellBundle = normalizeTranslationBundle(resources.shell);
  const routesBundle = normalizeTranslationBundle(resources.routes);

  deepMerge(compatibilityBundle, shellBundle);
  compatibilityBundle.routes = deepMerge(
    isPlainObject(compatibilityBundle.routes) ? { ...compatibilityBundle.routes } : {},
    routesBundle,
  );

  for (const namespace of LEGACY_COMMON_ROOT_NAMESPACES) {
    const bundle = resources[namespace];
    if (bundle) {
      compatibilityBundle[namespace] = normalizeTranslationBundle(bundle);
    }
  }

  return compatibilityBundle;
}