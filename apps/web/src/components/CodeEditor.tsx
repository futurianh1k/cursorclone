"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Editor, { Monaco } from "@monaco-editor/react";
import type { editor } from "monaco-editor";
import { getFileContent, updateFileContent } from "@/lib/api";

/**
 * 코드 선택 영역
 */
interface CodeSelection {
  startLine: number;
  endLine: number;
}

/**
 * CodeEditor Props
 */
interface CodeEditorProps {
  /** 워크스페이스 ID */
  workspaceId: string;
  /** 편집할 파일 경로 */
  filePath?: string;
  /** 코드 선택 영역 변경 콜백 */
  onSelectionChange?: (selection: CodeSelection | null) => void;
  /** 내용 변경 콜백 */
  onContentChange?: (content: string) => void;
}

/**
 * Monaco 에디터 기반 코드 편집기
 * 
 * 기능:
 * - 파일 로드/저장
 * - 자동 저장 (2초 debounce)
 * - Ctrl+S 단축키
 * - 언어별 구문 강조
 * - 선택 영역 감지
 */
export default function CodeEditor({
  workspaceId,
  filePath,
  onSelectionChange,
  onContentChange,
}: CodeEditorProps) {
  const [content, setContent] = useState("");
  const [originalContent, setOriginalContent] = useState("");
  const [language, setLanguage] = useState("python");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

  useEffect(() => {
    if (filePath) {
      loadFile();
    } else {
      setContent("");
    }
  }, [workspaceId, filePath]);

  // 파일 저장 함수
  const saveFile = useCallback(async (contentToSave: string) => {
    if (!filePath || saving) return;
    
    try {
      setSaving(true);
      await updateFileContent(workspaceId, filePath, contentToSave);
      setOriginalContent(contentToSave);
      setSaved(true);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save file");
    } finally {
      setSaving(false);
    }
  }, [workspaceId, filePath, saving]);

  // 자동 저장 (debounce 2초)
  const scheduleAutoSave = useCallback((newContent: string) => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    saveTimeoutRef.current = setTimeout(() => {
      saveFile(newContent);
    }, 2000);
  }, [saveFile]);

  // 컴포넌트 언마운트 시 저장
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  const loadFile = async () => {
    if (!filePath) return;

    try {
      setLoading(true);
      setError(null);
      const fileData = await getFileContent(workspaceId, filePath);
      setContent(fileData.content);
      setOriginalContent(fileData.content);
      setSaved(true);
      onContentChange?.(fileData.content);

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
    const newContent = value || "";
    setContent(newContent);
    onContentChange?.(newContent);
    
    // 변경 감지 및 자동 저장 스케줄
    if (newContent !== originalContent) {
      setSaved(false);
      scheduleAutoSave(newContent);
    }
  };

  /**
   * 에디터 마운트 핸들러
   * 
   * 단축키 및 이벤트 리스너 설정
   */
  const handleEditorMount = (
    editor: editor.IStandaloneCodeEditor,
    monaco: Monaco
  ): void => {
    editorRef.current = editor;
    
    // Ctrl+S / Cmd+S 저장 단축키
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
      saveFile(content);
    });
    
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
        role="status"
        aria-live="polite"
        aria-busy="true"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          fontSize: "14px",
          color: "#666",
        }}
      >
        <span aria-label="파일 로딩 중">Loading...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        aria-live="assertive"
        style={{
          padding: "12px",
          fontSize: "13px",
          color: "#d32f2f",
        }}
      >
        <span aria-label="오류">Error: {error}</span>
      </div>
    );
  }

  return (
    <div 
      style={{ height: "100%", display: "flex", flexDirection: "column" }}
      role="region"
      aria-label={filePath ? `코드 에디터: ${filePath}` : "코드 에디터"}
    >
      {/* 저장 상태 표시 */}
      <div 
        style={{ 
          padding: "4px 12px", 
          fontSize: "11px", 
          backgroundColor: "#f8f9fa",
          borderBottom: "1px solid #eee",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
        role="status"
        aria-live="polite"
      >
        <span style={{ color: "#666" }}>
          {saving ? (
            <span aria-label="저장 중">💾 저장 중...</span>
          ) : saved ? (
            <span aria-label="저장 완료">✅ 저장됨</span>
          ) : (
            <span aria-label="변경 사항 있음">⚠️ 변경됨 (자동 저장 대기)</span>
          )}
        </span>
        <button
          onClick={() => saveFile(content)}
          disabled={saving || saved}
          aria-label={saving ? "저장 중..." : saved ? "저장됨" : "파일 저장 (Ctrl+S)"}
          aria-disabled={saving || saved}
          style={{
            padding: "2px 8px",
            fontSize: "11px",
            backgroundColor: (saving || saved) ? "#e0e0e0" : "#007acc",
            color: (saving || saved) ? "#666" : "white",
            border: "none",
            borderRadius: "4px",
            cursor: (saving || saved) ? "default" : "pointer",
          }}
        >
          {saving ? "저장 중..." : "저장 (Ctrl+S)"}
        </button>
      </div>
      
      {/* 에디터 */}
      <div 
        style={{ flex: 1 }}
        role="textbox"
        aria-multiline="true"
        aria-label={`${language} 코드 편집기`}
      >
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
            // 접근성 옵션
            accessibilitySupport: "on",
            ariaLabel: filePath ? `${filePath} 편집 중` : "코드 편집기",
          }}
        />
      </div>
    </div>
  );
}
