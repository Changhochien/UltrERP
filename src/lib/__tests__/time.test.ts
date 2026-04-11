import { describe, expect, it } from "vitest";

import { formatBackendCalendarDate } from "../time";

describe("formatBackendCalendarDate", () => {
  it("keeps date-only backend values on the same calendar day", () => {
    expect(formatBackendCalendarDate("2024-05-01", "MM/dd")).toBe("05/01");
    expect(formatBackendCalendarDate("2024-05-01", "yyyy-MM-dd")).toBe("2024-05-01");
  });

  it("still formats full ISO timestamps through date-fns", () => {
    expect(formatBackendCalendarDate("2024-05-01T12:34:56Z", "yyyy-MM-dd")).toBe("2024-05-01");
  });
});