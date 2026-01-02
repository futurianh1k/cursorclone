"use client";

import { useState, useEffect } from "react";
import { getFileTree, FileTreeItem, createFile } from "@/lib/api";

interface FileTreeProps {
  workspaceId: string;
  onFileSelect?: (path: string) => void;
}

export default function FileTree({ workspaceId, onFileSelect }: FileTreeProps) {
  const [tree, setTree] = useState<FileTreeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [showNewFileInput, setShowNewFileInput] = useState(false);
  const [newFileName, setNewFileName] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadFileTree();
  }, [workspaceId]);

  const loadFileTree = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getFileTree(workspaceId);
      setTree(data.tree);
      // 루트 디렉토리 확장
      if (data.tree.length > 0) {
        setExpanded(new Set([data.tree[0].path]));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load file tree");
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (path: string) => {
    const newExpanded = new Set(expanded);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpanded(newExpanded);
  };

  const handleCreateFile = async () => {
    if (!newFileName.trim()) return;
    
    try {
      setCreating(true);
      await createFile(workspaceId, newFileName.trim());
      setNewFileName("");
      setShowNewFileInput(false);
      await loadFileTree();
      onFileSelect?.(newFileName.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create file");
    } finally {
      setCreating(false);
    }
  };

  const renderTreeItem = (item: FileTreeItem, level: number = 0) => {
    const isExpanded = expanded.has(item.path);
    const hasChildren = item.children && item.children.length > 0;

    return (
      <div key={item.path}>
        <div
          style={{
            padding: "4px 8px",
            paddingLeft: `${level * 16 + 8}px`,
            cursor: item.type === "directory" ? "pointer" : "default",
            display: "flex",
            alignItems: "center",
            gap: "4px",
            backgroundColor: "transparent",
            transition: "background-color 0.2s",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = "#f5f5f5";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "transparent";
          }}
          onClick={() => {
            if (item.type === "directory") {
              toggleExpand(item.path);
            } else {
              onFileSelect?.(item.path);
            }
          }}
        >
          {item.type === "directory" && (
            <span style={{ fontSize: "12px" }}>{isExpanded ? "📂" : "📁"}</span>
          )}
          {item.type === "file" && <span style={{ fontSize: "12px" }}>📄</span>}
          <span style={{ fontSize: "13px" }}>{item.name}</span>
        </div>
        {item.type === "directory" && isExpanded && hasChildren && (
          <div>
            {item.children!.map((child) => renderTreeItem(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div style={{ padding: "12px", fontSize: "12px", color: "#666" }}>
        Loading...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "12px", fontSize: "12px", color: "#d32f2f" }}>
        Error: {error}
        <button
          onClick={loadFileTree}
          style={{ marginTop: "8px", padding: "4px 8px", fontSize: "12px" }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div style={{ overflowY: "auto", height: "100%", display: "flex", flexDirection: "column" }}>
      {/* 새 파일 생성 버튼 */}
      <div style={{ padding: "8px", borderBottom: "1px solid #eee" }}>
        {!showNewFileInput ? (
          <button
            onClick={() => setShowNewFileInput(true)}
            style={{
              width: "100%",
              padding: "6px 12px",
              fontSize: "12px",
              backgroundColor: "#f0f0f0",
              border: "1px solid #ddd",
              borderRadius: "4px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "4px",
            }}
          >
            <span>📄</span> New File
          </button>
        ) : (
          <div style={{ display: "flex", gap: "4px" }}>
            <input
              type="text"
              value={newFileName}
              onChange={(e) => setNewFileName(e.target.value)}
              placeholder="filename.py"
              onKeyDown={(e) => {
                if (e.key === "Enter") handleCreateFile();
                if (e.key === "Escape") {
                  setShowNewFileInput(false);
                  setNewFileName("");
                }
              }}
              autoFocus
              style={{
                flex: 1,
                padding: "4px 8px",
                fontSize: "12px",
                border: "1px solid #007acc",
                borderRadius: "4px",
                outline: "none",
              }}
              disabled={creating}
            />
            <button
              onClick={handleCreateFile}
              disabled={creating || !newFileName.trim()}
              style={{
                padding: "4px 8px",
                fontSize: "12px",
                backgroundColor: "#007acc",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: creating ? "not-allowed" : "pointer",
              }}
            >
              ✓
            </button>
            <button
              onClick={() => {
                setShowNewFileInput(false);
                setNewFileName("");
              }}
              disabled={creating}
              style={{
                padding: "4px 8px",
                fontSize: "12px",
                backgroundColor: "#6c757d",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              ✕
            </button>
          </div>
        )}
      </div>
      
      {/* 파일 트리 */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {tree.length === 0 ? (
          <div style={{ padding: "12px", fontSize: "12px", color: "#666", textAlign: "center" }}>
            No files yet. Create a new file to get started.
          </div>
        ) : (
          tree.map((item) => renderTreeItem(item))
        )}
      </div>
    </div>
  );
}
