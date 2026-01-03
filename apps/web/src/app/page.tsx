"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import FileTree from "@/components/FileTree";
import CodeEditor from "@/components/CodeEditor";
import AIChat from "@/components/AIChat";
import WorkspaceSelector from "@/components/WorkspaceSelector";
import { listWorkspaces, deleteWorkspace, Workspace } from "@/lib/api";
import { getCurrentUser } from "@/lib/auth-api";

export default function Home() {
  const router = useRouter();
  const [workspaceId, setWorkspaceId] = useState<string>("");
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentFile, setCurrentFile] = useState<string | undefined>();
  const [fileContent, setFileContent] = useState<string | undefined>();
  const [selection, setSelection] = useState<{ startLine: number; endLine: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [showSelector, setShowSelector] = useState(false);

  useEffect(() => {
    // 인증 확인
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    // 사용자 확인
    getCurrentUser(token).catch(() => {
      localStorage.removeItem("access_token");
      router.push("/login");
    });

    loadWorkspaces();
  }, [router]);

  const loadWorkspaces = async () => {
    try {
      setLoading(true);
      const wsList = await listWorkspaces();
      setWorkspaces(wsList);
      if (wsList.length > 0) {
        setWorkspaceId(wsList[0].workspaceId);
        setShowSelector(false);
      } else {
        setShowSelector(true);
      }
    } catch (err) {
      console.error("Failed to load workspaces:", err);
      setShowSelector(true);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (path: string) => {
    setCurrentFile(path);
    setFileContent(undefined); // 파일 변경 시 초기화, CodeEditor에서 로드 후 설정
    setSelection(null);
  };

  const handleWorkspaceSelect = (workspace: Workspace) => {
    setWorkspaces([...workspaces, workspace]);
    setWorkspaceId(workspace.workspaceId);
    setShowSelector(false);
  };

  const handleDeleteWorkspace = async (wsId: string) => {
    if (!confirm(`워크스페이스 "${wsId}"를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없으며, 모든 파일이 영구적으로 삭제됩니다.`)) {
      return;
    }

    try {
      await deleteWorkspace(wsId);

      // 삭제된 워크스페이스를 목록에서 제거
      const updatedWorkspaces = workspaces.filter(ws => ws.workspaceId !== wsId);
      setWorkspaces(updatedWorkspaces);

      // 현재 선택된 워크스페이스가 삭제된 경우
      if (workspaceId === wsId) {
        if (updatedWorkspaces.length > 0) {
          setWorkspaceId(updatedWorkspaces[0].workspaceId);
        } else {
          setWorkspaceId("");
          setShowSelector(true);
        }
        setCurrentFile(undefined);
        setSelection(null);
      }

      alert("워크스페이스가 성공적으로 삭제되었습니다.");
    } catch (error) {
      console.error("Failed to delete workspace:", error);
      alert(`워크스페이스 삭제 실패: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  };

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          fontSize: "14px",
        }}
      >
        Loading workspaces...
      </div>
    );
  }

  if (showSelector || workspaces.length === 0) {
    return (
      <WorkspaceSelector
        onWorkspaceSelect={handleWorkspaceSelect}
        onCancel={() => setShowSelector(false)}
      />
    );
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "280px 1fr 360px", height: "100vh", overflow: "hidden" }}>
      <aside style={{ borderRight: "1px solid #ddd", display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <div style={{ padding: "12px", borderBottom: "1px solid #ddd" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <h3 style={{ margin: 0, fontSize: "16px" }}>Workspace</h3>
            <button
              onClick={() => setShowSelector(true)}
              style={{
                padding: "4px 8px",
                fontSize: "12px",
                backgroundColor: "#24292e",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              +
            </button>
          </div>
          <div style={{ display: "flex", gap: "4px" }}>
            <select
              value={workspaceId}
              onChange={(e) => {
                setWorkspaceId(e.target.value);
                setCurrentFile(undefined);
                setSelection(null);
              }}
              style={{
                flex: 1,
                padding: "4px 8px",
                fontSize: "12px",
                border: "1px solid #ddd",
                borderRadius: "4px",
              }}
            >
              {workspaces.map((ws) => (
                <option key={ws.workspaceId} value={ws.workspaceId}>
                  {ws.name}
                </option>
              ))}
            </select>
            <button
              onClick={() => handleDeleteWorkspace(workspaceId)}
              disabled={!workspaceId}
              title="워크스페이스 삭제"
              style={{
                padding: "4px 8px",
                fontSize: "12px",
                backgroundColor: "#dc2626",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: workspaceId ? "pointer" : "not-allowed",
                opacity: workspaceId ? 1 : 0.5,
              }}
            >
              🗑️
            </button>
          </div>
        </div>
        <div style={{ flex: 1, overflow: "hidden" }}>
          <FileTree workspaceId={workspaceId} onFileSelect={handleFileSelect} />
        </div>
      </aside>

      <main style={{ borderRight: "1px solid #ddd", display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {currentFile ? (
          <div style={{ flex: 1, overflow: "hidden" }}>
            <div
              style={{
                padding: "8px 12px",
                borderBottom: "1px solid #ddd",
                fontSize: "13px",
                backgroundColor: "#f5f5f5",
              }}
            >
              {currentFile}
            </div>
            <CodeEditor
              workspaceId={workspaceId}
              filePath={currentFile}
              onSelectionChange={setSelection}
              onContentChange={setFileContent}
            />
          </div>
        ) : (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              fontSize: "14px",
              color: "#666",
            }}
          >
            파일을 선택하세요
          </div>
        )}
      </main>

      <section style={{ display: "flex", flexDirection: "column", overflow: "hidden", height: "100%" }}>
        <AIChat
          workspaceId={workspaceId}
          currentFile={currentFile}
          fileContent={fileContent}
          selection={selection || undefined}
        />
      </section>
    </div>
  );
}
