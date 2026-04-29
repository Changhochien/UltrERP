import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SettingField } from "./SettingField";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe("SettingField", () => {
  it("edits a masked sensitive setting without exposing the stored value", () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const onReset = vi.fn().mockResolvedValue(undefined);

    render(
      <SettingField
        item={{
          key: "legacy_db_password",
          value: "",
          display_value: "********",
          value_type: "str",
          allowed_values: null,
          nullable: true,
          is_null: false,
          is_sensitive: true,
          description: "Legacy PostgreSQL password",
          category: "legacy_import",
          updated_at: null,
          updated_by: null,
        }}
        onSave={onSave}
        onReset={onReset}
      />,
    );

    const input = screen.getByPlaceholderText("********") as HTMLInputElement;
    expect(input.value).toBe("");

    fireEvent.change(input, { target: { value: "super-secret" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    expect(onSave).toHaveBeenCalledWith("legacy_db_password", "super-secret", "str");
  });
});
