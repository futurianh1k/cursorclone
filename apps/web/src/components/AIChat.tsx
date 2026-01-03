"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  advancedChatWithAI,
  uploadImage,
  suggestContext,
  validatePatch,
  applyPatch,
  AIAdvancedChatResponse,
  ContextItem,
  ContextType,
  ContextSuggestion,
  AIMode,
} from "@/lib/api";

interface AIChatProps {
  workspaceId: string;
  currentFile?: string;
  fileContent?: string;
  selection?: { startLine: number; endLine: number };
}

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  mode?: AIMode;
  timestamp: Date;
}

const MODES: { id: AIMode; icon: string; label: string; shortLabel: string; color: string }[] = [
  { id: "agent", icon: "⚡", label: "Agent", shortLabel: "Agent", color: "#7c3aed" },
  { id: "ask", icon: "💬", label: "Ask", shortLabel: "Ask", color: "#007acc" },
  { id: "plan", icon: "📋", label: "Plan", shortLabel: "Plan", color: "#059669" },
  { id: "debug", icon: "🐛", label: "Debug", shortLabel: "Debug", color: "#dc2626" },
];

export default function AIChat({
  workspaceId,
  currentFile,
  fileContent,
  selection,
}: AIChatProps) {
  // 상태
  const [message, setMessage] = useState("");
  const [mode, setMode] = useState<AIMode>("agent");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 컨텍스트
  const [contexts, setContexts] = useState<ContextItem[]>([]);
  const [showModeMenu, setShowModeMenu] = useState(false);
  const [showContextMenu, setShowContextMenu] = useState(false);
  const [contextQuery, setContextQuery] = useState("");
  const [contextSuggestions, setContextSuggestions] = useState<ContextSuggestion[]>([]);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(0);
  
  // Diff/Patch
  const [pendingDiff, setPendingDiff] = useState<string | null>(null);
  const [applyingPatch, setApplyingPatch] = useState(false);
  
  // Refs
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const modeMenuRef = useRef<HTMLDivElement>(null);
  const contextMenuRef = useRef<HTMLDivElement>(null);

  // 자동 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 텍스트 영역 높이 조절
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [message]);

  // 메뉴 외부 클릭 감지
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modeMenuRef.current && !modeMenuRef.current.contains(e.target as Node)) {
        setShowModeMenu(false);
      }
      if (contextMenuRef.current && !contextMenuRef.current.contains(e.target as Node)) {
        setShowContextMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // 현재 모드 정보
  const currentMode = MODES.find((m) => m.id === mode) || MODES[0];

  // @ 입력 감지
  const handleInputChange = async (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setMessage(value);

    const cursorPos = e.target.selectionStart;
    const textBefore = value.slice(0, cursorPos);
    const atMatch = textBefore.match(/@(\w*)$/);

    if (atMatch) {
      setContextQuery(atMatch[1]);
      setShowContextMenu(true);
      setSelectedSuggestionIndex(0);
      try {
        const result = await suggestContext(workspaceId, atMatch[1]);
        setContextSuggestions(result.suggestions);
      } catch {
        setContextSuggestions([]);
      }
    } else {
      setShowContextMenu(false);
    }
  };

  // 컨텍스트 선택
  const selectContext = (suggestion: ContextSuggestion) => {
    const cursorPos = textareaRef.current?.selectionStart || 0;
    const textBefore = message.slice(0, cursorPos);
    const textAfter = message.slice(cursorPos);
    const atIndex = textBefore.lastIndexOf("@");
    
    const newMessage = textBefore.slice(0, atIndex) + textAfter;
    setMessage(newMessage);
    setShowContextMenu(false);

    setContexts((prev) => [
      ...prev,
      {
        type: suggestion.type,
        path: suggestion.path,
        name: suggestion.name,
      },
    ]);

    textareaRef.current?.focus();
  };

  // 키보드 이벤트
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showContextMenu && contextSuggestions.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedSuggestionIndex((i) => Math.min(i + 1, contextSuggestions.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedSuggestionIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        selectContext(contextSuggestions[selectedSuggestionIndex]);
      } else if (e.key === "Escape") {
        setShowContextMenu(false);
      }
      return;
    }

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // 이미지 업로드
  const handleImageUpload = async (file: File) => {
    if (!file.type.startsWith("image/")) return;
    try {
      const result = await uploadImage(file);
      setContexts((prev) => [
        ...prev,
        {
          type: "image" as ContextType,
          imageUrl: result.imageUrl,
          name: file.name,
          mimeType: result.mimeType,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "이미지 업로드 실패");
    }
  };

  // 클립보드 붙여넣기
  const handlePaste = useCallback(async (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (const item of Array.from(items)) {
      if (item.type.startsWith("image/")) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) await handleImageUpload(file);
        return;
      }
    }
  }, []);

  // 드래그 앤 드롭
  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    const file = Array.from(e.dataTransfer.files).find((f) => f.type.startsWith("image/"));
    if (file) await handleImageUpload(file);
  };

  // 컨텍스트 제거
  const removeContext = (index: number) => {
    setContexts((prev) => prev.filter((_, i) => i !== index));
  };

  // 제출
  const handleSubmit = async () => {
    if (!message.trim() || loading) return;

    const userMessage = message.trim();
    const messageId = Date.now().toString();
    
    setMessages((prev) => [
      ...prev,
      { id: messageId, role: "user", content: userMessage, mode, timestamp: new Date() },
    ]);
    setMessage("");
    setContexts([]);
    setLoading(true);
    setError(null);

    try {
      const response = await advancedChatWithAI({
        workspaceId,
        message: userMessage,
        mode,
        contexts: contexts.length > 0 ? contexts : undefined,
        currentFile,
        currentContent: fileContent,
        currentSelection: selection,
      });

      // 응답 포맷팅
      let content = response.response;

      if (response.fileChanges?.length) {
        const firstDiff = response.fileChanges.find((c) => c.diff);
        if (firstDiff?.diff) {
          setPendingDiff(firstDiff.diff);
        }
      }

      setMessages((prev) => [
        ...prev,
        {
          id: `${messageId}-response`,
          role: "assistant",
          content,
          mode: response.mode,
          timestamp: new Date(),
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "요청 실패");
    } finally {
      setLoading(false);
    }
  };

  // 패치 적용
  const handleApplyPatch = async () => {
    if (!pendingDiff) return;

    setApplyingPatch(true);
    try {
      const validation = await validatePatch({ workspaceId, patch: pendingDiff });
      if (!validation.valid) {
        setError(`패치 검증 실패: ${validation.reason}`);
        return;
      }

      const result = await applyPatch({ workspaceId, patch: pendingDiff, dryRun: false });
      if (result.success) {
        setPendingDiff(null);
        setMessages((prev) => [
          ...prev,
          {
            id: `patch-${Date.now()}`,
            role: "system",
            content: `✅ 패치 적용 완료: ${result.appliedFiles.join(", ")}`,
            timestamp: new Date(),
          },
        ]);
      } else {
        setError(result.message || "패치 적용 실패");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "패치 적용 실패");
    } finally {
      setApplyingPatch(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        backgroundColor: "#1e1e1e",
        color: "#d4d4d4",
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      }}
    >
      {/* 헤더 */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid #333",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "18px" }}>{currentMode.icon}</span>
          <span style={{ fontWeight: 600, fontSize: "14px" }}>{currentMode.label}</span>
        </div>
        {currentFile && (
          <div
            style={{
              fontSize: "11px",
              color: "#888",
              backgroundColor: "#2d2d2d",
              padding: "4px 8px",
              borderRadius: "4px",
            }}
          >
            📄 {currentFile.split("/").pop()}
          </div>
        )}
      </div>

      {/* 메시지 영역 */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              textAlign: "center",
              padding: "40px 20px",
              color: "#666",
            }}
          >
            <div style={{ fontSize: "48px", marginBottom: "16px" }}>✨</div>
            <div style={{ fontSize: "16px", fontWeight: 500, marginBottom: "8px" }}>
              무엇을 도와드릴까요?
            </div>
            <div style={{ fontSize: "13px", color: "#888" }}>
              코드 작성, 디버깅, 리팩토링 등 무엇이든 물어보세요
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: msg.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            <div
              style={{
                maxWidth: "90%",
                padding: "12px 16px",
                borderRadius: msg.role === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                backgroundColor:
                  msg.role === "user"
                    ? currentMode.color
                    : msg.role === "system"
                    ? "#2d4a3e"
                    : "#2d2d2d",
                color: msg.role === "user" ? "white" : "#d4d4d4",
                fontSize: "13px",
                lineHeight: "1.6",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {msg.content}
            </div>
            <div
              style={{
                fontSize: "10px",
                color: "#666",
                marginTop: "4px",
                paddingLeft: msg.role === "user" ? 0 : "8px",
                paddingRight: msg.role === "user" ? "8px" : 0,
              }}
            >
              {msg.role === "user" ? "You" : msg.role === "system" ? "System" : "AI"}
              {msg.mode && ` • ${MODES.find((m) => m.id === msg.mode)?.label}`}
            </div>
          </div>
        ))}

        {loading && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "12px 16px",
              backgroundColor: "#2d2d2d",
              borderRadius: "16px 16px 16px 4px",
              maxWidth: "90%",
            }}
          >
            <div className="loading-dots" style={{ display: "flex", gap: "4px" }}>
              <span style={{ animation: "pulse 1.4s infinite", animationDelay: "0s" }}>●</span>
              <span style={{ animation: "pulse 1.4s infinite", animationDelay: "0.2s" }}>●</span>
              <span style={{ animation: "pulse 1.4s infinite", animationDelay: "0.4s" }}>●</span>
            </div>
            <span style={{ fontSize: "13px", color: "#888" }}>생각하는 중...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 패치 미리보기 */}
      {pendingDiff && (
        <div
          style={{
            margin: "0 16px 16px",
            padding: "12px",
            backgroundColor: "#1a2634",
            borderRadius: "8px",
            border: "1px solid #2d4a5e",
          }}
        >
          <div style={{ fontSize: "12px", fontWeight: 600, marginBottom: "8px", color: "#58a6ff" }}>
            📝 변경 사항 미리보기
          </div>
          <pre
            style={{
              fontSize: "11px",
              backgroundColor: "#0d1117",
              padding: "8px",
              borderRadius: "4px",
              overflow: "auto",
              maxHeight: "150px",
              margin: 0,
            }}
          >
            {pendingDiff}
          </pre>
          <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
            <button
              onClick={handleApplyPatch}
              disabled={applyingPatch}
              style={{
                flex: 1,
                padding: "8px",
                backgroundColor: applyingPatch ? "#333" : "#238636",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: applyingPatch ? "not-allowed" : "pointer",
                fontSize: "12px",
                fontWeight: 500,
              }}
            >
              {applyingPatch ? "적용 중..." : "✓ 적용"}
            </button>
            <button
              onClick={() => setPendingDiff(null)}
              disabled={applyingPatch}
              style={{
                flex: 1,
                padding: "8px",
                backgroundColor: "#333",
                color: "#d4d4d4",
                border: "1px solid #444",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "12px",
              }}
            >
              ✕ 취소
            </button>
          </div>
        </div>
      )}

      {/* 에러 메시지 */}
      {error && (
        <div
          style={{
            margin: "0 16px 16px",
            padding: "10px 12px",
            backgroundColor: "#3d1f1f",
            border: "1px solid #5c2626",
            borderRadius: "6px",
            fontSize: "12px",
            color: "#f87171",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>⚠️ {error}</span>
          <button
            onClick={() => setError(null)}
            style={{
              background: "none",
              border: "none",
              color: "#f87171",
              cursor: "pointer",
              fontSize: "14px",
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* 입력 영역 */}
      <div
        style={{
          padding: "16px",
          borderTop: "1px solid #333",
          backgroundColor: "#252525",
        }}
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
      >
        {/* 컨텍스트 태그 */}
        {contexts.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "10px" }}>
            {contexts.map((ctx, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "4px 10px",
                  backgroundColor: "#3d3d3d",
                  borderRadius: "12px",
                  fontSize: "11px",
                }}
              >
                <span>
                  {ctx.type === "file" && "📄"}
                  {ctx.type === "folder" && "📁"}
                  {ctx.type === "image" && "🖼️"}
                </span>
                <span style={{ maxWidth: "120px", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {ctx.name || ctx.path}
                </span>
                <button
                  onClick={() => removeContext(i)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#888",
                    cursor: "pointer",
                    padding: 0,
                    fontSize: "12px",
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        {/* 입력 필드 */}
        <div style={{ position: "relative" }}>
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder="무엇이든 물어보세요... (Shift+Enter: 줄바꿈)"
            disabled={loading}
            style={{
              width: "100%",
              padding: "12px 100px 12px 12px",
              fontSize: "13px",
              backgroundColor: "#1e1e1e",
              border: "1px solid #404040",
              borderRadius: "12px",
              color: "#d4d4d4",
              resize: "none",
              minHeight: "44px",
              maxHeight: "150px",
              outline: "none",
              fontFamily: "inherit",
              lineHeight: "1.5",
              boxSizing: "border-box",
            }}
          />

          {/* 버튼 그룹 (우측) */}
          <div
            style={{
              position: "absolute",
              right: "8px",
              bottom: "8px",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            {/* 이미지 업로드 */}
            <button
              onClick={() => fileInputRef.current?.click()}
              style={{
                padding: "6px",
                backgroundColor: "transparent",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                color: "#888",
                fontSize: "16px",
              }}
              title="이미지 첨부"
            >
              🖼️
            </button>

            {/* 컨텍스트 추가 */}
            <button
              onClick={() => {
                setMessage((prev) => prev + "@");
                textareaRef.current?.focus();
              }}
              style={{
                padding: "6px 8px",
                backgroundColor: "transparent",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                color: "#888",
                fontSize: "14px",
                fontWeight: 600,
              }}
              title="컨텍스트 추가 (@)"
            >
              @
            </button>

            {/* 전송 버튼 */}
            <button
              onClick={handleSubmit}
              disabled={loading || !message.trim()}
              style={{
                padding: "6px 12px",
                backgroundColor: loading || !message.trim() ? "#404040" : currentMode.color,
                border: "none",
                borderRadius: "6px",
                cursor: loading || !message.trim() ? "not-allowed" : "pointer",
                color: "white",
                fontSize: "14px",
                fontWeight: 500,
                display: "flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              {loading ? "..." : "↑"}
            </button>
          </div>

          {/* 컨텍스트 자동완성 메뉴 */}
          {showContextMenu && contextSuggestions.length > 0 && (
            <div
              ref={contextMenuRef}
              style={{
                position: "absolute",
                bottom: "100%",
                left: 0,
                right: 0,
                marginBottom: "4px",
                backgroundColor: "#2d2d2d",
                border: "1px solid #404040",
                borderRadius: "8px",
                maxHeight: "200px",
                overflowY: "auto",
                zIndex: 100,
                boxShadow: "0 -4px 12px rgba(0,0,0,0.3)",
              }}
            >
              {contextSuggestions.map((s, i) => (
                <div
                  key={i}
                  onClick={() => selectContext(s)}
                  style={{
                    padding: "10px 12px",
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    cursor: "pointer",
                    backgroundColor: i === selectedSuggestionIndex ? "#3d3d3d" : "transparent",
                    borderBottom: i < contextSuggestions.length - 1 ? "1px solid #333" : "none",
                  }}
                >
                  <span style={{ fontSize: "16px" }}>
                    {s.type === "file" ? "📄" : "📁"}
                  </span>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 500 }}>{s.name}</div>
                    {s.path && (
                      <div style={{ fontSize: "11px", color: "#888" }}>{s.path}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 하단 툴바 - 모드 선택 */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginTop: "10px",
          }}
        >
          {/* 모드 선택 드롭다운 */}
          <div style={{ position: "relative" }} ref={modeMenuRef}>
            <button
              onClick={() => setShowModeMenu(!showModeMenu)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                backgroundColor: "#3d3d3d",
                border: "1px solid #505050",
                borderRadius: "6px",
                cursor: "pointer",
                color: "#d4d4d4",
                fontSize: "12px",
                fontWeight: 500,
              }}
            >
              <span style={{ color: currentMode.color }}>{currentMode.icon}</span>
              <span>{currentMode.label}</span>
              <span style={{ fontSize: "10px", color: "#888" }}>▼</span>
            </button>

            {showModeMenu && (
              <div
                style={{
                  position: "absolute",
                  bottom: "100%",
                  left: 0,
                  marginBottom: "4px",
                  backgroundColor: "#2d2d2d",
                  border: "1px solid #404040",
                  borderRadius: "8px",
                  overflow: "hidden",
                  minWidth: "160px",
                  boxShadow: "0 -4px 12px rgba(0,0,0,0.3)",
                  zIndex: 100,
                }}
              >
                {MODES.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => {
                      setMode(m.id);
                      setShowModeMenu(false);
                    }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                      width: "100%",
                      padding: "10px 14px",
                      backgroundColor: mode === m.id ? "#3d3d3d" : "transparent",
                      border: "none",
                      cursor: "pointer",
                      color: "#d4d4d4",
                      fontSize: "13px",
                      textAlign: "left",
                    }}
                  >
                    <span style={{ color: m.color, fontSize: "16px" }}>{m.icon}</span>
                    <span style={{ fontWeight: mode === m.id ? 600 : 400 }}>{m.label}</span>
                    {mode === m.id && (
                      <span style={{ marginLeft: "auto", color: m.color }}>✓</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 단축키 안내 */}
          <div style={{ fontSize: "11px", color: "#666" }}>
            <span style={{ marginRight: "12px" }}>
              <kbd style={{ backgroundColor: "#3d3d3d", padding: "2px 6px", borderRadius: "3px" }}>@</kbd>{" "}
              파일 추가
            </span>
            <span>
              <kbd style={{ backgroundColor: "#3d3d3d", padding: "2px 6px", borderRadius: "3px" }}>⌘V</kbd>{" "}
              이미지
            </span>
          </div>
        </div>
      </div>

      {/* 숨겨진 파일 입력 */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleImageUpload(file);
          e.target.value = "";
        }}
        style={{ display: "none" }}
      />

      {/* 애니메이션 스타일 */}
      <style jsx>{`
        @keyframes pulse {
          0%, 80%, 100% { opacity: 0.3; }
          40% { opacity: 1; }
        }
        textarea::placeholder {
          color: #666;
        }
        textarea:focus {
          border-color: ${currentMode.color} !important;
        }
      `}</style>
    </div>
  );
}
