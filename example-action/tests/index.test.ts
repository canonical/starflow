import { describe, it, expect, vi } from "vitest";

// Mock @actions/core before importing your module so GitHub Actions env calls
// don't throw during tests.
vi.mock("@actions/core");

describe("example-action", () => {
  it("placeholder — replace with real tests", () => {
    expect(true).toBe(true);
  });
});
