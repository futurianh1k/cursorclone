"use client";

import { useState, useEffect } from "react";
import { getFileTree, FileTreeItem } from "@/lib/api";

interface FileTreeProps {
  workspaceId: string;
  onFileSelect?: (path: string) => void;
}

export default function FileTree({ workspaceId, onFileSelect }: FileTreeProps) {
  const [tree, setTree] = useState<FileTreeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

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
    <div style={{ overflowY: "auto", height: "100%" }}>
      {tree.map((item) => renderTreeItem(item))}
    </div>
  );
}
