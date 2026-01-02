"use client";

import { useState, useEffect } from "react";
import FileTree from "@/components/FileTree";
import CodeEditor from "@/components/CodeEditor";
import AIChat from "@/components/AIChat";
import { listWorkspaces, Workspace } from "@/lib/api";

export default function Home() {
  const [workspaceId, setWorkspaceId] = useState<string>("");
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentFile, setCurrentFile] = useState<string | undefined>();
  const [selection, setSelection] = useState<{ startLine: number; endLine: number } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadWorkspaces();
  }, []);

  const loadWorkspaces = async () => {
    try {
      setLoading(true);
      const wsList = await listWorkspaces();
      setWorkspaces(wsList);
      if (wsList.length > 0) {
        setWorkspaceId(wsList[0].workspaceId);
      }
    } catch (err) {
      console.error("Failed to load workspaces:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (path: string) => {
    setCurrentFile(path);
    setSelection(null);
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

  if (workspaces.length === 0) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          fontSize: "14px",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        <div>No workspaces found.</div>
        <div style={{ fontSize: "12px", color: "#666" }}>
          개발 모드: DEV_MODE=true 환경변수로 API를 실행하면 ~/cctv-fastapi가 자동으로 워크스페이스로 등록됩니다.
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "280px 1fr 360px", height: "100vh" }}>
      <aside style={{ borderRight: "1px solid #ddd", display: "flex", flexDirection: "column" }}>
        <div style={{ padding: "12px", borderBottom: "1px solid #ddd" }}>
          <h3 style={{ margin: "0 0 8px 0", fontSize: "16px" }}>Workspace</h3>
          <select
            value={workspaceId}
            onChange={(e) => {
              setWorkspaceId(e.target.value);
              setCurrentFile(undefined);
              setSelection(null);
            }}
            style={{
              width: "100%",
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
        </div>
        <div style={{ flex: 1, overflow: "hidden" }}>
          <FileTree workspaceId={workspaceId} onFileSelect={handleFileSelect} />
        </div>
      </aside>

      <main style={{ borderRight: "1px solid #ddd", display: "flex", flexDirection: "column" }}>
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

      <section style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <AIChat
          workspaceId={workspaceId}
          currentFile={currentFile}
          selection={selection || undefined}
        />
      </section>
    </div>
  );
}
