"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  listProjects,
  Project,
  listWorkspaces,
  deleteWorkspace,
  createWorkspace,
  cloneGitHubRepository,
  Workspace,
  listIDEContainers,
  createIDEContainer,
  startIDEContainer,
  stopIDEContainer,
  deleteIDEContainer,
  IDEContainerResponse,
  updateProject,
  deleteProject,
} from "@/lib/api";
import { getCurrentUser, User } from "@/lib/auth-api";
import { groupWorkspacesByProject } from "@/lib/projectGrouping";

// IDE 컨테이너 상태 색상
const STATUS_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  running: { bg: "#dcfce7", text: "#166534", label: "실행 중" },
  starting: { bg: "#fef3c7", text: "#92400e", label: "시작 중" },
  pending: { bg: "#fef3c7", text: "#92400e", label: "대기 중" },
  stopped: { bg: "#f3f4f6", text: "#4b5563", label: "중지됨" },
  stopping: { bg: "#fef3c7", text: "#92400e", label: "중지 중" },
  error: { bg: "#fee2e2", text: "#991b1b", label: "오류" },
  none: { bg: "#f3f4f6", text: "#9ca3af", label: "미생성" },
};

export default function DashboardOverview() {
  const [user, setUser] = useState<User | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [containers, setContainers] = useState<Record<string, IDEContainerResponse>>({});
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [expandedProjectIds, setExpandedProjectIds] = useState<Set<string>>(new Set());
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);
  const [editingProjectName, setEditingProjectName] = useState<string>("");
  const [projectActionLoading, setProjectActionLoading] = useState<string | null>(null);
  const [projectDeleteConfirm, setProjectDeleteConfirm] = useState<string | null>(null);

  // 워크스페이스 생성 모달
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createMode, setCreateMode] = useState<"empty" | "github">("empty");
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [newProjectName, setNewProjectName] = useState<string>("");
  const [githubUrl, setGithubUrl] = useState("");
  const [githubBranch, setGithubBranch] = useState("");
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // 데이터 로드
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem("access_token");
      if (token) {
        const userData = await getCurrentUser(token);
        setUser(userData);
      }
      try {
        const projectList = await listProjects();
        setProjects(projectList);
      } catch {
        console.warn("프로젝트 목록 조회 실패");
        setProjects([]);
      }
      const wsList = await listWorkspaces();
      setWorkspaces(wsList);

      // 모든 IDE 컨테이너 조회 (한 번에)
      const containerMap: Record<string, IDEContainerResponse> = {};
      try {
        const result = await listIDEContainers();
        // 워크스페이스 ID로 그룹화
        for (const container of result.containers) {
          // 워크스페이스 ID와 매칭 (컨테이너 이름에서도 추출)
          const wsId = container.workspaceId;
          if (!containerMap[wsId]) {
            containerMap[wsId] = container;
          }
        }
      } catch {
        console.warn("IDE 컨테이너 목록 조회 실패");
      }
      setContainers(containerMap);
    } catch (err) {
      console.error("Failed to load data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const projectNameById = useCallback(() => {
    const map: Record<string, string> = {};
    for (const p of projects) map[p.projectId] = p.name;
    return map;
  }, [projects]);

  // 프로젝트 카드 기본 확장(처음 로드 시)
  useEffect(() => {
    if (expandedProjectIds.size > 0) return;
    const next = new Set<string>();
    for (const p of projects) next.add(p.projectId);
    setExpandedProjectIds(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projects]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 워크스페이스 생성
  const handleCreateWorkspace = async () => {
    if (createMode === "empty" && !newWorkspaceName.trim()) {
      setCreateError("워크스페이스 이름을 입력하세요");
      return;
    }
    if (createMode === "github" && !githubUrl.trim()) {
      setCreateError("GitHub URL을 입력하세요");
      return;
    }

    setCreateLoading(true);
    setCreateError(null);

    try {
      let workspace: Workspace;
      const projectId = selectedProjectId.trim() || undefined;
      const projectName =
        projectId ? undefined : (newProjectName.trim() || newWorkspaceName.trim() || undefined);

      if (createMode === "empty") {
        workspace = await createWorkspace(newWorkspaceName.trim(), {
          projectId,
          projectName,
        });
      } else {
        workspace = await cloneGitHubRepository({
          repositoryUrl: githubUrl.trim(),
          name: newWorkspaceName.trim() || undefined,
          branch: githubBranch.trim() || undefined,
          projectId,
          projectName,
        });
      }

      // 워크스페이스가 생성되면 IDE 컨테이너도 생성
      try {
        const container = await createIDEContainer({
          workspaceId: workspace.workspaceId,
        });
        setContainers((prev) => ({
          ...prev,
          [workspace.workspaceId]: container,
        }));
      } catch (containerErr) {
        console.warn("IDE 컨테이너 생성 실패:", containerErr);
      }

      setWorkspaces((prev) => [...prev, workspace]);
      // 프로젝트 자동 생성 케이스 반영을 위해 projects 재조회
      try {
        const projectList = await listProjects();
        setProjects(projectList);
      } catch {
        // noop
      }
      setShowCreateModal(false);
      setNewWorkspaceName("");
      setSelectedProjectId("");
      setNewProjectName("");
      setGithubUrl("");
      setGithubBranch("");
      setSuccessMessage(`워크스페이스 "${workspace.name}"가 생성되었습니다`);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      const message = err instanceof Error ? err.message : "생성에 실패했습니다";
      setCreateError(message);
    } finally {
      setCreateLoading(false);
    }
  };

  // IDE 시작
  const handleStartIDE = async (workspaceId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setActionLoading(workspaceId);
    setError(null);

    try {
      const container = containers[workspaceId];

      if (container) {
        // 기존 컨테이너가 있으면 시작
        if (container.status === "stopped") {
          const result = await startIDEContainer(container.containerId);
          setContainers((prev) => ({
            ...prev,
            [workspaceId]: { ...prev[workspaceId], status: result.status, url: result.url },
          }));
          // 시작되면 URL로 이동
          if (result.url) {
            window.open(result.url, "_blank");
          }
        } else if (container.status === "running" && container.url) {
          // 이미 실행 중이면 바로 열기
          window.open(container.url, "_blank");
        }
      } else {
        // 컨테이너가 없으면 새로 생성
        const newContainer = await createIDEContainer({ workspaceId });
        setContainers((prev) => ({
          ...prev,
          [workspaceId]: newContainer,
        }));
        // 생성 후 URL로 이동
        if (newContainer.url) {
          window.open(newContainer.url, "_blank");
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "IDE 시작에 실패했습니다";
      setError(message);
    } finally {
      setActionLoading(null);
    }
  };

  // IDE 중지 (상태 보존)
  const handleStopIDE = async (workspaceId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setActionLoading(workspaceId);
    setError(null);

    try {
      const container = containers[workspaceId];
      if (container && container.status === "running") {
        const result = await stopIDEContainer(container.containerId);
        setContainers((prev) => ({
          ...prev,
          [workspaceId]: { ...prev[workspaceId], status: result.status },
        }));
        setSuccessMessage("IDE가 중지되었습니다. 다시 시작하면 이전 상태가 복원됩니다.");
        setTimeout(() => setSuccessMessage(null), 3000);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "IDE 중지에 실패했습니다";
      setError(message);
    } finally {
      setActionLoading(null);
    }
  };

  // 워크스페이스 삭제 (컨테이너 포함)
  const handleDeleteWorkspace = async (workspaceId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (deleteConfirm !== workspaceId) {
      setDeleteConfirm(workspaceId);
      return;
    }

    setActionLoading(workspaceId);
    setError(null);

    try {
      // 먼저 IDE 컨테이너 삭제
      const container = containers[workspaceId];
      if (container) {
        try {
          await deleteIDEContainer(container.containerId);
        } catch (containerErr) {
          console.warn("IDE 컨테이너 삭제 실패:", containerErr);
        }
      }

      // 워크스페이스 삭제
      await deleteWorkspace(workspaceId);
      setWorkspaces((prev) => prev.filter((ws) => ws.workspaceId !== workspaceId));
      setContainers((prev) => {
        const newContainers = { ...prev };
        delete newContainers[workspaceId];
        return newContainers;
      });
      setDeleteConfirm(null);
      setSuccessMessage("워크스페이스가 삭제되었습니다");
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      const message = err instanceof Error ? err.message : "삭제에 실패했습니다";
      setError(message);
    } finally {
      setActionLoading(null);
    }
  };

  // 삭제 확인 취소
  const handleCancelDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDeleteConfirm(null);
  };

  // 컨테이너 상태 가져오기
  const getContainerStatus = (workspaceId: string) => {
    const container = containers[workspaceId];
    if (!container) return "none";
    return container.status;
  };

  const openCreateModalForProject = (projectId?: string) => {
    setCreateError(null);
    setShowCreateModal(true);
    setCreateMode("empty");
    setNewWorkspaceName("");
    setGithubUrl("");
    setGithubBranch("");
    if (projectId) {
      setSelectedProjectId(projectId);
      setNewProjectName("");
    } else {
      setSelectedProjectId("");
      setNewProjectName("");
    }
  };

  const toggleProject = (projectId: string) => {
    setExpandedProjectIds((prev) => {
      const next = new Set(prev);
      if (next.has(projectId)) next.delete(projectId);
      else next.add(projectId);
      return next;
    });
  };

  const expandAllProjects = () => {
    const next = new Set<string>();
    for (const p of projects) next.add(p.projectId);
    setExpandedProjectIds(next);
  };

  const collapseAllProjects = () => {
    setExpandedProjectIds(new Set());
  };

  const startEditProject = (projectId: string, currentName: string) => {
    setProjectDeleteConfirm(null);
    setEditingProjectId(projectId);
    setEditingProjectName(currentName);
  };

  const cancelEditProject = () => {
    setEditingProjectId(null);
    setEditingProjectName("");
  };

  const saveProjectName = async (projectId: string) => {
    const nextName = editingProjectName.trim();
    if (!nextName) {
      setError("프로젝트 이름은 비워둘 수 없습니다.");
      return;
    }
    setProjectActionLoading(projectId);
    setError(null);
    try {
      const updated = await updateProject(projectId, nextName);
      setProjects((prev) => prev.map((p) => (p.projectId === projectId ? { ...p, name: updated.name } : p)));
      setSuccessMessage("프로젝트 이름이 변경되었습니다");
      setTimeout(() => setSuccessMessage(null), 3000);
      cancelEditProject();
    } catch (err) {
      const message = err instanceof Error ? err.message : "프로젝트 이름 변경에 실패했습니다";
      setError(message);
    } finally {
      setProjectActionLoading(null);
    }
  };

  const requestDeleteProject = (projectId: string) => {
    cancelEditProject();
    setProjectDeleteConfirm(projectId);
  };

  const cancelDeleteProject = () => {
    setProjectDeleteConfirm(null);
  };

  const confirmDeleteProject = async (projectId: string, workspaceCount: number) => {
    if (workspaceCount > 0) {
      setError("워크스페이스가 있는 프로젝트는 삭제할 수 없습니다. 먼저 워크스페이스를 삭제하세요.");
      setProjectDeleteConfirm(null);
      return;
    }

    setProjectActionLoading(projectId);
    setError(null);
    try {
      await deleteProject(projectId);
      setProjects((prev) => prev.filter((p) => p.projectId !== projectId));
      setExpandedProjectIds((prev) => {
        const next = new Set(prev);
        next.delete(projectId);
        return next;
      });
      if (selectedProjectId === projectId) setSelectedProjectId("");
      setProjectDeleteConfirm(null);
      setSuccessMessage("프로젝트가 삭제되었습니다");
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      const message = err instanceof Error ? err.message : "프로젝트 삭제에 실패했습니다";
      setError(message);
    } finally {
      setProjectActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "40px", textAlign: "center" }}>
        로딩 중...
      </div>
    );
  }

  return (
    <div style={{ padding: "32px", maxWidth: "1200px", margin: "0 auto" }}>
      {/* 헤더 */}
      <div style={{ marginBottom: "32px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "28px", fontWeight: 600 }}>
            Workspaces
          </h1>
          <p style={{ margin: "8px 0 0 0", color: "#656d76", fontSize: "16px" }}>
            환영합니다, {user?.name}님! VSCode 서버 워크스페이스를 관리하세요.
          </p>
        </div>
        <button
          onClick={() => openCreateModalForProject(undefined)}
          style={{
            padding: "12px 24px",
            fontSize: "14px",
            fontWeight: 600,
            backgroundColor: "#238636",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <span style={{ fontSize: "18px" }}>+</span> 새 워크스페이스
        </button>
      </div>

      {/* 성공 메시지 */}
      {successMessage && (
        <div
          style={{
            padding: "12px 16px",
            marginBottom: "16px",
            backgroundColor: "#dcfce7",
            border: "1px solid #22c55e",
            borderRadius: "6px",
            color: "#166534",
            fontSize: "14px",
          }}
        >
          ✓ {successMessage}
        </div>
      )}

      {/* 오류 메시지 */}
      {error && (
        <div
          style={{
            padding: "12px 16px",
            marginBottom: "16px",
            backgroundColor: "#ffeef0",
            border: "1px solid #f85149",
            borderRadius: "6px",
            color: "#cf222e",
            fontSize: "14px",
          }}
        >
          {error}
          <button
            onClick={() => setError(null)}
            style={{
              marginLeft: "12px",
              background: "none",
              border: "none",
              color: "#cf222e",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            ✕
          </button>
        </div>
      )}

      {/* 통계 카드 */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "16px",
          marginBottom: "32px",
        }}
      >
        <StatCard
          title="프로젝트"
          value={projects.length}
          icon="🧩"
          color="#8250df"
        />
        <StatCard
          title="워크스페이스"
          value={workspaces.length}
          icon="📁"
          color="#0366d6"
        />
        <StatCard
          title="실행 중인 IDE"
          value={Object.values(containers).filter((c) => c.status === "running").length}
          icon="🟢"
          color="#28a745"
        />
        <StatCard
          title="중지된 IDE"
          value={Object.values(containers).filter((c) => c.status === "stopped").length}
          icon="⏸️"
          color="#6c757d"
        />
      </div>

      {/* 워크스페이스 목록 */}
      <div
        style={{
          backgroundColor: "white",
          borderRadius: "8px",
          border: "1px solid #d1d5da",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: "16px 24px",
            borderBottom: "1px solid #d1d5da",
            backgroundColor: "#f6f8fa",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 600 }}>
            프로젝트
          </h2>
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              onClick={expandAllProjects}
              style={{
                padding: "6px 10px",
                fontSize: "12px",
                backgroundColor: "#ffffff",
                color: "#24292e",
                border: "1px solid #d1d5da",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              모두 펼치기
            </button>
            <button
              onClick={collapseAllProjects}
              style={{
                padding: "6px 10px",
                fontSize: "12px",
                backgroundColor: "#ffffff",
                color: "#24292e",
                border: "1px solid #d1d5da",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              모두 접기
            </button>
          </div>
        </div>

        {workspaces.length === 0 ? (
          <div style={{ padding: "60px 40px", textAlign: "center", color: "#656d76" }}>
            <div style={{ fontSize: "48px", marginBottom: "16px" }}>📂</div>
            <p style={{ fontSize: "16px", marginBottom: "16px" }}>
              워크스페이스가 없습니다.
            </p>
            <button
              onClick={() => openCreateModalForProject(undefined)}
              style={{
                padding: "10px 20px",
                fontSize: "14px",
                fontWeight: 500,
                backgroundColor: "#238636",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              첫 워크스페이스 만들기
            </button>
          </div>
        ) : (
          <div>
            {(() => {
              const { groups, unassigned } = groupWorkspacesByProject(projects, workspaces);
              const byProjectName = projectNameById();

              const renderWorkspaceRow = (ws: Workspace) => {
                const status = getContainerStatus(ws.workspaceId);
                const statusInfo = STATUS_COLORS[status] || STATUS_COLORS.none;
                const container = containers[ws.workspaceId];
                const isLoading = actionLoading === ws.workspaceId;

                return (
                  <div
                    key={ws.workspaceId}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "16px",
                      padding: "16px 24px",
                      borderTop: "1px solid #f1f3f5",
                      backgroundColor: deleteConfirm === ws.workspaceId ? "#fff5f5" : "transparent",
                      transition: "background-color 0.2s",
                    }}
                  >
                    <div
                      style={{
                        width: "40px",
                        height: "40px",
                        borderRadius: "8px",
                        backgroundColor: statusInfo.bg,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "20px",
                      }}
                    >
                      {status === "running" ? "💻" : status === "stopped" ? "⏸️" : "📁"}
                    </div>

                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                        <span style={{ fontSize: "15px", fontWeight: 600 }}>{ws.name}</span>
                        <span
                          style={{
                            padding: "2px 8px",
                            fontSize: "12px",
                            fontWeight: 500,
                            backgroundColor: statusInfo.bg,
                            color: statusInfo.text,
                            borderRadius: "12px",
                          }}
                        >
                          {statusInfo.label}
                        </span>
                      </div>
                      <div style={{ fontSize: "13px", color: "#656d76" }}>
                        {ws.rootPath}
                        {container?.port && status === "running" && (
                          <span style={{ marginLeft: "12px", color: "#0366d6" }}>포트: {container.port}</span>
                        )}
                      </div>
                    </div>

                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      {deleteConfirm === ws.workspaceId ? (
                        <>
                          <span style={{ fontSize: "13px", color: "#cf222e", marginRight: "8px" }}>
                            삭제하시겠습니까?
                          </span>
                          <button
                            onClick={(e) => handleDeleteWorkspace(ws.workspaceId, e)}
                            disabled={isLoading}
                            style={{
                              padding: "8px 16px",
                              fontSize: "13px",
                              fontWeight: 500,
                              backgroundColor: "#cf222e",
                              color: "white",
                              border: "none",
                              borderRadius: "6px",
                              cursor: isLoading ? "not-allowed" : "pointer",
                              opacity: isLoading ? 0.6 : 1,
                            }}
                          >
                            {isLoading ? "삭제 중..." : "확인"}
                          </button>
                          <button
                            onClick={handleCancelDelete}
                            disabled={isLoading}
                            style={{
                              padding: "8px 16px",
                              fontSize: "13px",
                              fontWeight: 500,
                              backgroundColor: "#f6f8fa",
                              color: "#24292e",
                              border: "1px solid #d1d5da",
                              borderRadius: "6px",
                              cursor: "pointer",
                            }}
                          >
                            취소
                          </button>
                        </>
                      ) : (
                        <>
                          {status === "running" ? (
                            <>
                              <button
                                onClick={(e) => handleStartIDE(ws.workspaceId, e)}
                                disabled={isLoading}
                                style={{
                                  padding: "8px 16px",
                                  fontSize: "13px",
                                  fontWeight: 500,
                                  backgroundColor: "#0366d6",
                                  color: "white",
                                  border: "none",
                                  borderRadius: "6px",
                                  cursor: isLoading ? "not-allowed" : "pointer",
                                  opacity: isLoading ? 0.6 : 1,
                                }}
                              >
                                {isLoading ? "..." : "🔗 열기"}
                              </button>
                              <button
                                onClick={(e) => handleStopIDE(ws.workspaceId, e)}
                                disabled={isLoading}
                                title="IDE 중지 (상태 보존)"
                                style={{
                                  padding: "8px 16px",
                                  fontSize: "13px",
                                  fontWeight: 500,
                                  backgroundColor: "#f6f8fa",
                                  color: "#24292e",
                                  border: "1px solid #d1d5da",
                                  borderRadius: "6px",
                                  cursor: isLoading ? "not-allowed" : "pointer",
                                }}
                              >
                                ⏸️ 중지
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={(e) => handleStartIDE(ws.workspaceId, e)}
                              disabled={isLoading || status === "starting" || status === "pending"}
                              style={{
                                padding: "8px 16px",
                                fontSize: "13px",
                                fontWeight: 500,
                                backgroundColor: "#238636",
                                color: "white",
                                border: "none",
                                borderRadius: "6px",
                                cursor: isLoading || status === "starting" ? "not-allowed" : "pointer",
                                opacity: isLoading || status === "starting" ? 0.6 : 1,
                              }}
                            >
                              {isLoading || status === "starting" || status === "pending" ? "시작 중..." : "▶ 시작"}
                            </button>
                          )}
                          <button
                            onClick={(e) => handleDeleteWorkspace(ws.workspaceId, e)}
                            disabled={isLoading}
                            title="워크스페이스 삭제"
                            style={{
                              padding: "8px 12px",
                              fontSize: "13px",
                              fontWeight: 500,
                              backgroundColor: "transparent",
                              color: "#656d76",
                              border: "1px solid #d1d5da",
                              borderRadius: "6px",
                              cursor: "pointer",
                            }}
                          >
                            🗑️
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                );
              };

              const renderProjectCard = (projectId: string, projectName: string, list: Workspace[]) => {
                const expanded = expandedProjectIds.has(projectId);
                const running = list.filter((w) => getContainerStatus(w.workspaceId) === "running").length;
                const stopped = list.filter((w) => getContainerStatus(w.workspaceId) === "stopped").length;
                const manageable = projects.some((p) => p.projectId === projectId);
                const isEditing = editingProjectId === projectId;
                const isDeleting = projectDeleteConfirm === projectId;
                const isActionLoading = projectActionLoading === projectId;

                return (
                  <div key={projectId} style={{ borderBottom: "1px solid #d1d5da" }}>
                    <div
                      style={{
                        padding: "14px 24px",
                        backgroundColor: "#ffffff",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "12px",
                      }}
                    >
                      <button
                        onClick={() => toggleProject(projectId)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "10px",
                          background: "transparent",
                          border: "none",
                          cursor: "pointer",
                          padding: 0,
                          textAlign: "left",
                          flex: 1,
                        }}
                        aria-label={`프로젝트 ${projectName} ${expanded ? "접기" : "펼치기"}`}
                      >
                        <span style={{ fontSize: "14px", color: "#656d76" }}>{expanded ? "▾" : "▸"}</span>
                        <div>
                          <div style={{ fontSize: "14px", fontWeight: 700 }}>
                            {isEditing ? (
                              <input
                                value={editingProjectName}
                                onChange={(e) => setEditingProjectName(e.target.value)}
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                }}
                                style={{
                                  width: "320px",
                                  maxWidth: "60vw",
                                  padding: "6px 8px",
                                  fontSize: "14px",
                                  border: "1px solid #d1d5da",
                                  borderRadius: "6px",
                                }}
                                aria-label="프로젝트 이름"
                              />
                            ) : (
                              projectName
                            )}
                          </div>
                          <div style={{ fontSize: "12px", color: "#9ca3af" }}>{projectId}</div>
                        </div>
                        <div style={{ display: "flex", gap: "10px", marginLeft: "16px", color: "#656d76", fontSize: "12px" }}>
                          <span>WS {list.length}</span>
                          <span>🟢 {running}</span>
                          <span>⏸️ {stopped}</span>
                        </div>
                      </button>

                      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                        {manageable && (
                          <>
                            {isEditing ? (
                              <>
                                <button
                                  onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    saveProjectName(projectId);
                                  }}
                                  disabled={isActionLoading}
                                  style={{
                                    padding: "8px 12px",
                                    fontSize: "12px",
                                    fontWeight: 600,
                                    backgroundColor: "#0366d6",
                                    color: "white",
                                    border: "none",
                                    borderRadius: "6px",
                                    cursor: isActionLoading ? "not-allowed" : "pointer",
                                    opacity: isActionLoading ? 0.7 : 1,
                                  }}
                                >
                                  {isActionLoading ? "저장 중..." : "저장"}
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    cancelEditProject();
                                  }}
                                  disabled={isActionLoading}
                                  style={{
                                    padding: "8px 12px",
                                    fontSize: "12px",
                                    fontWeight: 600,
                                    backgroundColor: "#f6f8fa",
                                    color: "#24292e",
                                    border: "1px solid #d1d5da",
                                    borderRadius: "6px",
                                    cursor: "pointer",
                                  }}
                                >
                                  취소
                                </button>
                              </>
                            ) : isDeleting ? (
                              <>
                                <button
                                  onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    confirmDeleteProject(projectId, list.length);
                                  }}
                                  disabled={isActionLoading}
                                  style={{
                                    padding: "8px 12px",
                                    fontSize: "12px",
                                    fontWeight: 700,
                                    backgroundColor: "#cf222e",
                                    color: "white",
                                    border: "none",
                                    borderRadius: "6px",
                                    cursor: isActionLoading ? "not-allowed" : "pointer",
                                    opacity: isActionLoading ? 0.7 : 1,
                                  }}
                                >
                                  {isActionLoading ? "삭제 중..." : "삭제 확인"}
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    cancelDeleteProject();
                                  }}
                                  disabled={isActionLoading}
                                  style={{
                                    padding: "8px 12px",
                                    fontSize: "12px",
                                    fontWeight: 600,
                                    backgroundColor: "#f6f8fa",
                                    color: "#24292e",
                                    border: "1px solid #d1d5da",
                                    borderRadius: "6px",
                                    cursor: "pointer",
                                  }}
                                >
                                  취소
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    startEditProject(projectId, projectName);
                                  }}
                                  style={{
                                    padding: "8px 12px",
                                    fontSize: "12px",
                                    fontWeight: 600,
                                    backgroundColor: "#f6f8fa",
                                    color: "#24292e",
                                    border: "1px solid #d1d5da",
                                    borderRadius: "6px",
                                    cursor: "pointer",
                                  }}
                                >
                                  ✏️ 이름 변경
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    requestDeleteProject(projectId);
                                  }}
                                  style={{
                                    padding: "8px 12px",
                                    fontSize: "12px",
                                    fontWeight: 600,
                                    backgroundColor: "transparent",
                                    color: "#cf222e",
                                    border: "1px solid #d1d5da",
                                    borderRadius: "6px",
                                    cursor: "pointer",
                                  }}
                                  title={list.length > 0 ? "워크스페이스가 있으면 삭제할 수 없습니다" : "프로젝트 삭제"}
                                >
                                  🗑️ 삭제
                                </button>
                              </>
                            )}
                          </>
                        )}

                        <button
                          onClick={() => openCreateModalForProject(projectId)}
                          style={{
                            padding: "8px 12px",
                            fontSize: "12px",
                            fontWeight: 600,
                            backgroundColor: "#238636",
                            color: "white",
                            border: "none",
                            borderRadius: "6px",
                            cursor: "pointer",
                          }}
                          aria-label={`${projectName}에 워크스페이스 추가`}
                        >
                          + 워크스페이스 추가
                        </button>
                      </div>
                    </div>
                    {expanded && (
                      <div>
                        {list.length === 0 ? (
                          <div style={{ padding: "16px 24px", color: "#656d76", borderTop: "1px solid #f1f3f5" }}>
                            워크스페이스가 없습니다. 우측의 “+ 워크스페이스 추가”로 생성하세요.
                          </div>
                        ) : (
                          list.map(renderWorkspaceRow)
                        )}
                      </div>
                    )}
                  </div>
                );
              };

              return (
                <>
                  {groups.map((g) => renderProjectCard(g.projectId, g.projectName, g.workspaces))}
                  {unassigned.length > 0 &&
                    renderProjectCard("unassigned", "미지정", unassigned)}
                  {groups.length === 0 && unassigned.length === 0 && (
                    <div style={{ padding: "40px 24px", color: "#656d76" }}>
                      표시할 프로젝트/워크스페이스가 없습니다.
                    </div>
                  )}
                </>
              );
            })()}
          </div>
        )}
      </div>

      {/* 워크스페이스 생성 모달 */}
      {showCreateModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={() => setShowCreateModal(false)}
        >
          <div
            style={{
              backgroundColor: "white",
              borderRadius: "12px",
              width: "100%",
              maxWidth: "500px",
              padding: "24px",
              boxShadow: "0 20px 40px rgba(0,0,0,0.2)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 style={{ margin: "0 0 24px 0", fontSize: "20px", fontWeight: 600 }}>
              새 워크스페이스 생성
            </h2>

            {/* 모드 선택 탭 */}
            <div style={{ display: "flex", gap: "8px", marginBottom: "24px" }}>
              <button
                onClick={() => setCreateMode("empty")}
                style={{
                  flex: 1,
                  padding: "10px",
                  fontSize: "14px",
                  fontWeight: 500,
                  backgroundColor: createMode === "empty" ? "#0366d6" : "#f6f8fa",
                  color: createMode === "empty" ? "white" : "#24292e",
                  border: "1px solid",
                  borderColor: createMode === "empty" ? "#0366d6" : "#d1d5da",
                  borderRadius: "6px",
                  cursor: "pointer",
                }}
              >
                📁 빈 워크스페이스
              </button>
              <button
                onClick={() => setCreateMode("github")}
                style={{
                  flex: 1,
                  padding: "10px",
                  fontSize: "14px",
                  fontWeight: 500,
                  backgroundColor: createMode === "github" ? "#0366d6" : "#f6f8fa",
                  color: createMode === "github" ? "white" : "#24292e",
                  border: "1px solid",
                  borderColor: createMode === "github" ? "#0366d6" : "#d1d5da",
                  borderRadius: "6px",
                  cursor: "pointer",
                }}
              >
                🔗 GitHub 클론
              </button>
            </div>

            {/* 폼 */}
            <div style={{ marginBottom: "16px" }}>
              <label style={{ display: "block", fontSize: "14px", fontWeight: 500, marginBottom: "8px" }}>
                프로젝트 (선택)
              </label>
              <select
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  fontSize: "14px",
                  border: "1px solid #d1d5da",
                  borderRadius: "6px",
                  boxSizing: "border-box",
                  backgroundColor: "white",
                }}
              >
                <option value="">새 프로젝트(자동 생성)</option>
                {projects.map((p) => (
                  <option key={p.projectId} value={p.projectId}>
                    {p.name} ({p.projectId})
                  </option>
                ))}
              </select>
              {!selectedProjectId && (
                <div style={{ marginTop: "10px" }}>
                  <label
                    style={{
                      display: "block",
                      fontSize: "13px",
                      fontWeight: 500,
                      marginBottom: "6px",
                      color: "#656d76",
                    }}
                  >
                    새 프로젝트 이름 (선택)
                  </label>
                  <input
                    type="text"
                    value={newProjectName}
                    onChange={(e) => setNewProjectName(e.target.value)}
                    placeholder="비우면 워크스페이스 이름을 사용"
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      fontSize: "14px",
                      border: "1px solid #d1d5da",
                      borderRadius: "6px",
                      boxSizing: "border-box",
                    }}
                  />
                </div>
              )}
            </div>

            <div style={{ marginBottom: "16px" }}>
              <label style={{ display: "block", fontSize: "14px", fontWeight: 500, marginBottom: "8px" }}>
                워크스페이스 이름 {createMode === "github" && "(선택사항)"}
              </label>
              <input
                type="text"
                value={newWorkspaceName}
                onChange={(e) => setNewWorkspaceName(e.target.value)}
                placeholder={createMode === "github" ? "저장소 이름 사용" : "my-project"}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  fontSize: "14px",
                  border: "1px solid #d1d5da",
                  borderRadius: "6px",
                  boxSizing: "border-box",
                }}
              />
            </div>

            {createMode === "github" && (
              <>
                <div style={{ marginBottom: "16px" }}>
                  <label style={{ display: "block", fontSize: "14px", fontWeight: 500, marginBottom: "8px" }}>
                    GitHub URL *
                  </label>
                  <input
                    type="text"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    placeholder="https://github.com/owner/repo"
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      fontSize: "14px",
                      border: "1px solid #d1d5da",
                      borderRadius: "6px",
                      boxSizing: "border-box",
                    }}
                  />
                </div>
                <div style={{ marginBottom: "16px" }}>
                  <label style={{ display: "block", fontSize: "14px", fontWeight: 500, marginBottom: "8px" }}>
                    브랜치 (선택사항)
                  </label>
                  <input
                    type="text"
                    value={githubBranch}
                    onChange={(e) => setGithubBranch(e.target.value)}
                    placeholder="main"
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      fontSize: "14px",
                      border: "1px solid #d1d5da",
                      borderRadius: "6px",
                      boxSizing: "border-box",
                    }}
                  />
                </div>
              </>
            )}

            {/* 오류 메시지 */}
            {createError && (
              <div
                style={{
                  padding: "12px",
                  marginBottom: "16px",
                  backgroundColor: "#ffeef0",
                  border: "1px solid #f85149",
                  borderRadius: "6px",
                  color: "#cf222e",
                  fontSize: "14px",
                }}
              >
                {createError}
              </div>
            )}

            {/* 버튼 */}
            <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setCreateError(null);
                  setNewWorkspaceName("");
                  setSelectedProjectId("");
                  setNewProjectName("");
                  setGithubUrl("");
                  setGithubBranch("");
                }}
                disabled={createLoading}
                style={{
                  padding: "10px 20px",
                  fontSize: "14px",
                  backgroundColor: "#f6f8fa",
                  color: "#24292e",
                  border: "1px solid #d1d5da",
                  borderRadius: "6px",
                  cursor: createLoading ? "not-allowed" : "pointer",
                }}
              >
                취소
              </button>
              <button
                onClick={handleCreateWorkspace}
                disabled={createLoading}
                style={{
                  padding: "10px 20px",
                  fontSize: "14px",
                  fontWeight: 500,
                  backgroundColor: "#238636",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: createLoading ? "not-allowed" : "pointer",
                  opacity: createLoading ? 0.6 : 1,
                }}
              >
                {createLoading ? "생성 중..." : "생성 및 IDE 시작"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
  color,
}: {
  title: string;
  value: number | string;
  icon: string;
  color: string;
}) {
  return (
    <div
      style={{
        backgroundColor: "white",
        padding: "20px",
        borderRadius: "8px",
        border: "1px solid #d1d5da",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
        <div style={{ fontSize: "24px" }}>{icon}</div>
        <div
          style={{
            fontSize: "32px",
            fontWeight: 600,
            color: color,
          }}
        >
          {typeof value === "number" ? value.toLocaleString() : value}
        </div>
      </div>
      <div style={{ fontSize: "14px", color: "#656d76" }}>{title}</div>
    </div>
  );
}
