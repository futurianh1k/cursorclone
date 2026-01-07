import { describe, it, expect } from "vitest";
import { groupWorkspacesByProject } from "@/lib/projectGrouping";

describe("groupWorkspacesByProject", () => {
  it("projects 순서를 우선으로 그룹핑하고, projectId 없는 워크스페이스는 unassigned로 분리한다", () => {
    const projects = [
      { projectId: "prj-a", name: "A", ownerId: "u", orgId: "o" },
      { projectId: "prj-b", name: "B", ownerId: "u", orgId: "o" },
    ];
    const workspaces = [
      { workspaceId: "ws-1", projectId: "prj-b", name: "W1", rootPath: "/w1" },
      { workspaceId: "ws-2", projectId: "prj-a", name: "W2", rootPath: "/w2" },
      { workspaceId: "ws-3", name: "W3", rootPath: "/w3" },
    ];

    const { groups, unassigned } = groupWorkspacesByProject(projects, workspaces);
    expect(groups.map((g) => g.projectId)).toEqual(["prj-a", "prj-b"]);
    expect(groups[0].workspaces.map((w) => w.workspaceId)).toEqual(["ws-2"]);
    expect(groups[1].workspaces.map((w) => w.workspaceId)).toEqual(["ws-1"]);
    expect(unassigned.map((w) => w.workspaceId)).toEqual(["ws-3"]);
  });
});

