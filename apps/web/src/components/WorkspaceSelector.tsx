"use client";

import { useState } from "react";
import { cloneGitHubRepository, createWorkspace, Workspace } from "@/lib/api";

interface WorkspaceSelectorProps {
  onWorkspaceSelect: (workspace: Workspace) => void;
  onCancel?: () => void;
}

export default function WorkspaceSelector({
  onWorkspaceSelect,
  onCancel,
}: WorkspaceSelectorProps) {
  const [mode, setMode] = useState<"select" | "github" | "create">("select");
  const [githubUrl, setGithubUrl] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const [branch, setBranch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGitHubClone = async () => {
    if (!githubUrl.trim()) {
      setError("GitHub 저장소 URL을 입력하세요");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const workspace = await cloneGitHubRepository({
        repositoryUrl: githubUrl.trim(),
        name: workspaceName.trim() || undefined,
        branch: branch.trim() || undefined,
      });
      onWorkspaceSelect(workspace);
    } catch (err) {
      const message = err instanceof Error ? err.message : "저장소 클론에 실패했습니다";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateWorkspace = async () => {
    if (!workspaceName.trim()) {
      setError("워크스페이스 이름을 입력하세요");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const workspace = await createWorkspace(workspaceName.trim());
      onWorkspaceSelect(workspace);
    } catch (err) {
      const message = err instanceof Error ? err.message : "워크스페이스 생성에 실패했습니다";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  if (mode === "select") {
    return (
      <div
        role="main"
        aria-labelledby="workspace-title"
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          gap: "24px",
          padding: "40px",
        }}
      >
        <h1
          id="workspace-title"
          style={{ fontSize: "24px", fontWeight: 600, marginBottom: "8px" }}
        >
          워크스페이스 선택
        </h1>
        <p style={{ fontSize: "14px", color: "#666", marginBottom: "32px" }}>
          새 워크스페이스를 생성하거나 GitHub 저장소를 클론하세요
        </p>

        <nav
          aria-label="워크스페이스 생성 옵션"
          style={{ display: "flex", gap: "12px", width: "100%", maxWidth: "400px" }}
        >
          <button
            onClick={() => setMode("github")}
            aria-label="GitHub 저장소 클론하기"
            style={{
              flex: 1,
              padding: "12px 24px",
              fontSize: "14px",
              fontWeight: 500,
              backgroundColor: "#24292e",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
            }}
          >
            GitHub 클론
          </button>
          <button
            onClick={() => setMode("create")}
            aria-label="빈 워크스페이스 생성하기"
            style={{
              flex: 1,
              padding: "12px 24px",
              fontSize: "14px",
              fontWeight: 500,
              backgroundColor: "#f6f8fa",
              color: "#24292e",
              border: "1px solid #d1d5da",
              borderRadius: "6px",
              cursor: "pointer",
            }}
          >
            빈 워크스페이스 생성
          </button>
        </nav>
      </div>
    );
  }

  if (mode === "github") {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          padding: "40px",
        }}
      >
        <div style={{ width: "100%", maxWidth: "500px" }}>
          <div style={{ fontSize: "20px", fontWeight: 600, marginBottom: "24px" }}>
            GitHub 저장소 클론
          </div>

          <div style={{ marginBottom: "16px" }}>
            <label
              style={{
                display: "block",
                fontSize: "14px",
                fontWeight: 500,
                marginBottom: "8px",
              }}
            >
              저장소 URL
            </label>
            <input
              type="text"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="https://github.com/owner/repo"
              style={{
                width: "100%",
                padding: "8px 12px",
                fontSize: "14px",
                border: "1px solid #d1d5da",
                borderRadius: "6px",
              }}
            />
          </div>

          <div style={{ marginBottom: "16px" }}>
            <label
              style={{
                display: "block",
                fontSize: "14px",
                fontWeight: 500,
                marginBottom: "8px",
              }}
            >
              워크스페이스 이름 (선택사항)
            </label>
            <input
              type="text"
              value={workspaceName}
              onChange={(e) => setWorkspaceName(e.target.value)}
              placeholder="자동으로 저장소 이름 사용"
              style={{
                width: "100%",
                padding: "8px 12px",
                fontSize: "14px",
                border: "1px solid #d1d5da",
                borderRadius: "6px",
              }}
            />
          </div>

          <div style={{ marginBottom: "24px" }}>
            <label
              style={{
                display: "block",
                fontSize: "14px",
                fontWeight: 500,
                marginBottom: "8px",
              }}
            >
              브랜치 (선택사항)
            </label>
            <input
              type="text"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              placeholder="main"
              style={{
                width: "100%",
                padding: "8px 12px",
                fontSize: "14px",
                border: "1px solid #d1d5da",
                borderRadius: "6px",
              }}
            />
          </div>

          {error && (
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
              {error}
            </div>
          )}

          <div style={{ display: "flex", gap: "12px" }}>
            <button
              onClick={() => {
                setMode("select");
                setError(null);
                setGithubUrl("");
                setWorkspaceName("");
                setBranch("");
              }}
              disabled={loading}
              style={{
                padding: "8px 16px",
                fontSize: "14px",
                backgroundColor: "#f6f8fa",
                color: "#24292e",
                border: "1px solid #d1d5da",
                borderRadius: "6px",
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? 0.6 : 1,
              }}
            >
              취소
            </button>
            <button
              onClick={handleGitHubClone}
              disabled={loading || !githubUrl.trim()}
              style={{
                flex: 1,
                padding: "8px 16px",
                fontSize: "14px",
                fontWeight: 500,
                backgroundColor: "#24292e",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: loading || !githubUrl.trim() ? "not-allowed" : "pointer",
                opacity: loading || !githubUrl.trim() ? 0.6 : 1,
              }}
            >
              {loading ? "클론 중..." : "클론"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (mode === "create") {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          padding: "40px",
        }}
      >
        <div style={{ width: "100%", maxWidth: "500px" }}>
          <div style={{ fontSize: "20px", fontWeight: 600, marginBottom: "24px" }}>
            빈 워크스페이스 생성
          </div>

          <div style={{ marginBottom: "24px" }}>
            <label
              style={{
                display: "block",
                fontSize: "14px",
                fontWeight: 500,
                marginBottom: "8px",
              }}
            >
              워크스페이스 이름
            </label>
            <input
              type="text"
              value={workspaceName}
              onChange={(e) => setWorkspaceName(e.target.value)}
              placeholder="my-project"
              style={{
                width: "100%",
                padding: "8px 12px",
                fontSize: "14px",
                border: "1px solid #d1d5da",
                borderRadius: "6px",
              }}
            />
          </div>

          {error && (
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
              {error}
            </div>
          )}

          <div style={{ display: "flex", gap: "12px" }}>
            <button
              onClick={() => {
                setMode("select");
                setError(null);
                setWorkspaceName("");
              }}
              disabled={loading}
              style={{
                padding: "8px 16px",
                fontSize: "14px",
                backgroundColor: "#f6f8fa",
                color: "#24292e",
                border: "1px solid #d1d5da",
                borderRadius: "6px",
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? 0.6 : 1,
              }}
            >
              취소
            </button>
            <button
              onClick={handleCreateWorkspace}
              disabled={loading || !workspaceName.trim()}
              style={{
                flex: 1,
                padding: "8px 16px",
                fontSize: "14px",
                fontWeight: 500,
                backgroundColor: "#24292e",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: loading || !workspaceName.trim() ? "not-allowed" : "pointer",
                opacity: loading || !workspaceName.trim() ? 0.6 : 1,
              }}
            >
              {loading ? "생성 중..." : "생성"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
