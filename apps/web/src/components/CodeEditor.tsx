"use client";

import { useState, useEffect } from "react";
import Editor from "@monaco-editor/react";
import { getFileContent, updateFileContent } from "@/lib/api";

interface CodeEditorProps {
  workspaceId: string;
  filePath?: string;
  onSelectionChange?: (selection: { startLine: number; endLine: number } | null) => void;
}

export default function CodeEditor({
  workspaceId,
  filePath,
  onSelectionChange,
}: CodeEditorProps) {
  const [content, setContent] = useState("");
  const [language, setLanguage] = useState("python");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (filePath) {
      loadFile();
    } else {
      setContent("");
    }
  }, [workspaceId, filePath]);

  const loadFile = async () => {
    if (!filePath) return;

    try {
      setLoading(true);
      setError(null);
      const fileData = await getFileContent(workspaceId, filePath);
      setContent(fileData.content);

      // 언어 감지
      const ext = filePath.split(".").pop()?.toLowerCase();
      const langMap: Record<string, string> = {
        py: "python",
        js: "javascript",
        ts: "typescript",
        tsx: "typescript",
        jsx: "javascript",
        java: "java",
        go: "go",
        rs: "rust",
        c: "c",
        cpp: "cpp",
        h: "c",
        hpp: "cpp",
        rb: "ruby",
        php: "php",
        swift: "swift",
        kt: "kotlin",
        scala: "scala",
        cs: "csharp",
        sql: "sql",
        sh: "shell",
        bash: "shell",
        yaml: "yaml",
        yml: "yaml",
        json: "json",
        md: "markdown",
        html: "html",
        css: "css",
        xml: "xml",
      };
      setLanguage(langMap[ext || ""] || "plaintext");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load file");
      setContent("");
    } finally {
      setLoading(false);
    }
  };

  const handleEditorChange = (value: string | undefined) => {
    setContent(value || "");
  };

  const handleEditorMount = (editor: any, monaco: any) => {
    // 선택 영역 변경 감지
    editor.onDidChangeCursorSelection(() => {
      const selection = editor.getSelection();
      if (selection && selection.startLineNumber !== selection.endLineNumber) {
        onSelectionChange?.({
          startLine: selection.startLineNumber,
          endLine: selection.endLineNumber,
        });
      } else {
        onSelectionChange?.(null);
      }
    });
  };

  if (loading) {
    return (
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
        Loading...
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          padding: "12px",
          fontSize: "13px",
          color: "#d32f2f",
        }}
      >
        Error: {error}
      </div>
    );
  }

  return (
    <Editor
      height="100%"
      language={language}
      value={content}
      onChange={handleEditorChange}
      onMount={handleEditorMount}
      options={{
        minimap: { enabled: false },
        fontSize: 14,
        wordWrap: "on",
        automaticLayout: true,
      }}
    />
  );
}
