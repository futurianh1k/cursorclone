import type { Project, Workspace } from "@/lib/api";

export type ProjectGroup = {
  projectId: string;
  projectName: string;
  workspaces: Workspace[];
};

/**
 * 프로젝트 기준으로 워크스페이스를 그룹핑한다.
 * - projects 목록에 없는 projectId는 "알 수 없는 프로젝트"로 처리
 * - projectId가 없는 워크스페이스는 "미지정" 그룹으로 분리
 */
export function groupWorkspacesByProject(
  projects: Project[],
  workspaces: Workspace[]
): {
  groups: ProjectGroup[];
  unassigned: Workspace[];
} {
  const nameById = new Map<string, string>();
  for (const p of projects) nameById.set(p.projectId, p.name);

  const unassigned: Workspace[] = [];
  const map = new Map<string, Workspace[]>();

  for (const ws of workspaces) {
    const pid = ws.projectId || null;
    if (!pid) {
      unassigned.push(ws);
      continue;
    }
    const list = map.get(pid) || [];
    list.push(ws);
    map.set(pid, list);
  }

  // stable ordering: projects order first (프로젝트가 비어 있어도 표시), then unknown groups
  const groups: ProjectGroup[] = [];
  const seen = new Set<string>();

  for (const p of projects) {
    const list = map.get(p.projectId) || [];
    groups.push({
      projectId: p.projectId,
      projectName: p.name,
      workspaces: list,
    });
    seen.add(p.projectId);
  }

  for (const [pid, list] of map.entries()) {
    if (seen.has(pid)) continue;
    groups.push({
      projectId: pid,
      projectName: nameById.get(pid) || "알 수 없는 프로젝트",
      workspaces: list,
    });
  }

  return { groups, unassigned };
}

