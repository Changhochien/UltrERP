/** Settings data hooks — wraps API calls with loading/error state. */

import { useCallback, useEffect, useState } from "react";

import {
  getSettings,
  getCategories,
  updateSetting,
  resetSetting,
  type SettingsCategory,
} from "../lib/api/settings";

export function useSettings() {
  const [categories, setCategories] = useState<SettingsCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getSettings();
      setCategories(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { categories, loading, error, refresh };
}

export function useUpdateSetting(onSuccess?: () => void, onError?: (err: Error) => void) {
  const [updating, setUpdating] = useState(false);

  const mutate = useCallback(
    async (key: string, value: string) => {
      setUpdating(true);
      try {
        await updateSetting(key, value);
        onSuccess?.();
      } catch (err) {
        onError?.(err instanceof Error ? err : new Error(String(err)));
      } finally {
        setUpdating(false);
      }
    },
    [onSuccess, onError],
  );

  return { updateSetting: mutate, updating };
}

export function useResetSetting(onSuccess?: () => void, onError?: (err: Error) => void) {
  const [resetting, setResetting] = useState(false);

  const mutate = useCallback(
    async (key: string) => {
      setResetting(true);
      try {
        await resetSetting(key);
        onSuccess?.();
      } catch (err) {
        onError?.(err instanceof Error ? err : new Error(String(err)));
      } finally {
        setResetting(false);
      }
    },
    [onSuccess, onError],
  );

  return { resetSetting: mutate, resetting };
}

export { getCategories };
