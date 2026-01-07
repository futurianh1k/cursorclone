import { describe, it, expect } from "vitest";
import { canDeleteProject } from "@/lib/projectManagement";

describe("canDeleteProject", () => {
  it("워크스페이스 0개일 때만 삭제 가능", () => {
    expect(canDeleteProject(0)).toBe(true);
    expect(canDeleteProject(1)).toBe(false);
    expect(canDeleteProject(10)).toBe(false);
  });
});

