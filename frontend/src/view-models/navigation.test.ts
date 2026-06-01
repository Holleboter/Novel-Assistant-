import { describe, expect, it } from "vitest";
import { primaryNavigationItems } from "./navigation";

describe("primaryNavigationItems", () => {
  it("exposes Skills as a first-level sidebar destination", () => {
    expect(primaryNavigationItems.map((item) => item.route)).toEqual([
      "hub",
      "skills",
      "graph",
      "settings",
    ]);
    expect(primaryNavigationItems.find((item) => item.route === "skills")?.label).toBe(
      "Skills",
    );
  });
});
