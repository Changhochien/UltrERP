import { describe, expect, it } from "vitest";

import { eventToShortcutStep } from "./shortcuts";

describe("eventToShortcutStep", () => {
  it("returns null when the keyboard event does not expose a string key", () => {
    const event = {
      key: undefined,
      code: "KeyK",
      ctrlKey: false,
      metaKey: false,
      altKey: false,
      shiftKey: false,
    } as unknown as KeyboardEvent;

    expect(eventToShortcutStep(event)).toBeNull();
  });

  it("continues to normalize ordinary modified keys", () => {
    const event = {
      key: "K",
      code: "KeyK",
      ctrlKey: true,
      metaKey: false,
      altKey: false,
      shiftKey: false,
    } as KeyboardEvent;

    expect(eventToShortcutStep(event)).toBe("mod+k");
  });
});