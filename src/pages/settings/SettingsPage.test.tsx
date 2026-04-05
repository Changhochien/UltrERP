import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import type { SettingsCategory } from "../../lib/api/settings";

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
	vi.resetModules();
});

// ── Mock data ─────────────────────────────────────────────────

const mockCategories: SettingsCategory[] = [
	{
		category: "general",
		description: "General settings",
		items: [
			{
				key: "log_level",
				value: "INFO",
				display_value: "INFO",
				value_type: "literal",
				allowed_values: ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
				nullable: false,
				is_null: false,
				is_sensitive: false,
				description: "Logging output level",
				category: "general",
				updated_at: null,
				updated_by: null,
			},
		],
	},
	{
		category: "egui",
		description: "eGui settings",
		items: [
			{
				key: "egui_tracking_enabled",
				value: "false",
				display_value: "false",
				value_type: "bool",
				allowed_values: null,
				nullable: false,
				is_null: false,
				is_sensitive: false,
				description: "Enable eGui approval request tracking",
				category: "egui",
				updated_at: null,
				updated_by: null,
			},
		],
	},
	{
		category: "auth",
		description: "Authentication settings",
		items: [
			{
				key: "jwt_secret",
				value: "********",
				display_value: "********",
				value_type: "str",
				allowed_values: null,
				nullable: false,
				is_null: false,
				is_sensitive: true,
				description: "JWT secret key",
				category: "auth",
				updated_at: null,
				updated_by: null,
			},
		],
	},
];

const mockRefresh = vi.fn();
const mockUpdate = vi.fn().mockResolvedValue({});
const mockReset = vi.fn().mockResolvedValue(undefined);

// ── Hook mock factory ───────────────────────────────────────

function makeUseSettingsReturn(categories: SettingsCategory[], loading = false, error: string | null = null) {
	return {
		categories,
		loading,
		error,
		refresh: mockRefresh,
	};
}

// ── Test cases ─────────────────────────────────────────────────

describe("SettingsPage", () => {
	it("renders all category tabs", async () => {
		vi.doMock("../../hooks/useSettings", () => ({
			useSettings: () => makeUseSettingsReturn(mockCategories),
			useUpdateSetting: () => ({ updateSetting: mockUpdate }),
			useResetSetting: () => ({ resetSetting: mockReset }),
		}));

		const { SettingsPage } = await import("./SettingsPage");
		render(<SettingsPage />);

		await waitFor(() => {
			expect(screen.getByRole("tab", { name: /general/i })).toBeTruthy();
		});
		expect(screen.getByRole("tab", { name: /egui/i })).toBeTruthy();
		expect(screen.getByRole("tab", { name: /auth/i })).toBeTruthy();
	});

	it("shows error state when fetch fails", async () => {
		vi.doMock("../../hooks/useSettings", () => ({
			useSettings: () => makeUseSettingsReturn([], false, "Failed to load settings"),
			useUpdateSetting: () => ({ updateSetting: mockUpdate }),
			useResetSetting: () => ({ resetSetting: mockReset }),
		}));

		const { SettingsPage } = await import("./SettingsPage");
		render(<SettingsPage />);

		expect(screen.getByText(/Failed to load settings/i)).toBeTruthy();
	});

	it("shows empty state when no categories returned", async () => {
		vi.doMock("../../hooks/useSettings", () => ({
			useSettings: () => makeUseSettingsReturn([], false, null),
			useUpdateSetting: () => ({ updateSetting: mockUpdate }),
			useResetSetting: () => ({ resetSetting: mockReset }),
		}));

		const { SettingsPage } = await import("./SettingsPage");
		render(<SettingsPage />);

		expect(screen.getByText(/No settings categories available/i)).toBeTruthy();
	});
});
