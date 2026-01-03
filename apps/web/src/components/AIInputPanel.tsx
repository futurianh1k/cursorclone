"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  uploadImage,
  suggestContext,
  advancedChatWithAI,
  ContextItem,
  ContextType,
  ContextSuggestion,
  AIAdvancedChatResponse,
  AIMode,
} from "@/lib/api";

interface AIInputPanelProps {
  workspaceId: string;
  currentFile?: string;
  fileContent?: string;
  selection?: { startLine: number; endLine: number };
  onResponse: (response: AIAdvancedChatResponse) => void;
  onError: (error: string) => void;
  disabled?: boolean;
}

const MODE_CONFIG: Record<AIMode, { icon: string; label: string; color: string; placeholder: string }> = {
  ask: {
    icon: "💬",
    label: "Ask",
    color: "#007acc",
    placeholder: "코드에 대해 질문하세요...",
  },
  agent: {
    icon: "🤖",
    label: "Agent",
    color: "#7c3aed",
    placeholder: "자동으로 코드를 변경합니다...",
  },
  plan: {
    icon: "📋",
    label: "Plan",
    color: "#059669",
    placeholder: "목표를 입력하세요...",
  },
  debug: {
    icon: "🐛",
    label: "Debug",
    color: "#dc2626",
    placeholder: "에러 메시지를 붙여넣으세요...",
  },
};

export default function AIInputPanel({
  workspaceId,
  currentFile,
  fileContent,
  selection,
  onResponse,
  onError,
  disabled = false,
}: AIInputPanelProps) {
  const [message, setMessage] = useState("");
  const [mode, setMode] = useState<AIMode>("ask");
  const [contexts, setContexts] = useState<ContextItem[]>([]);
  const [loading, setLoading] = useState(false);
  
  // @ mention 자동완성
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<ContextSuggestion[]>([]);
  const [suggestionQuery, setSuggestionQuery] = useState("");
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(0);
  
  // 이미지 업로드
  const [uploadingImage, setUploadingImage] = useState(false);
  
  // 히스토리
  const [history, setHistory] = useState<Array<{ role: string; content: string }>>([]);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // 텍스트 영역 자동 높이 조절
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + "px";
    }
  }, [message]);

  // @ 입력 감지 및 자동완성
  const handleInputChange = async (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setMessage(value);
    
    // @ 위치 찾기
    const cursorPos = e.target.selectionStart;
    const textBeforeCursor = value.slice(0, cursorPos);
    const atMatch = textBeforeCursor.match(/@(\w*)$/);
    
    if (atMatch) {
      const query = atMatch[1];
      setSuggestionQuery(query);
      setShowSuggestions(true);
      setSelectedSuggestionIndex(0);
      
      // 제안 가져오기
      try {
        const result = await suggestContext(workspaceId, query);
        setSuggestions(result.suggestions);
      } catch {
        setSuggestions([]);
      }
    } else {
      setShowSuggestions(false);
    }
  };

  // 제안 선택
  const selectSuggestion = (suggestion: ContextSuggestion) => {
    // @ 이후 텍스트를 제안으로 교체
    const cursorPos = textareaRef.current?.selectionStart || 0;
    const textBeforeCursor = message.slice(0, cursorPos);
    const textAfterCursor = message.slice(cursorPos);
    
    const atIndex = textBeforeCursor.lastIndexOf("@");
    const newText = textBeforeCursor.slice(0, atIndex) + `@${suggestion.name} ` + textAfterCursor;
    
    setMessage(newText);
    setShowSuggestions(false);
    
    // 컨텍스트에 추가
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

  // 키보드 네비게이션
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showSuggestions && suggestions.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedSuggestionIndex((prev) => Math.min(prev + 1, suggestions.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedSuggestionIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        selectSuggestion(suggestions[selectedSuggestionIndex]);
      } else if (e.key === "Escape") {
        setShowSuggestions(false);
      }
    } else if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // 이미지 업로드
  const handleImageUpload = async (file: File) => {
    if (!file.type.startsWith("image/")) {
      onError("이미지 파일만 업로드할 수 있습니다.");
      return;
    }
    
    setUploadingImage(true);
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
      onError(err instanceof Error ? err.message : "이미지 업로드 실패");
    } finally {
      setUploadingImage(false);
    }
  };

  // 파일 선택 핸들러
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleImageUpload(file);
    }
    e.target.value = "";
  };

  // 클립보드 붙여넣기
  const handlePaste = useCallback(async (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    
    for (const item of Array.from(items)) {
      // 이미지 붙여넣기
      if (item.type.startsWith("image/")) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) {
          await handleImageUpload(file);
        }
        return;
      }
    }
    
    // 텍스트 붙여넣기 (기본 동작)
  }, []);

  // 컨텍스트 제거
  const removeContext = (index: number) => {
    setContexts((prev) => prev.filter((_, i) => i !== index));
  };

  // 드래그 앤 드롭
  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    const imageFile = files.find((f) => f.type.startsWith("image/"));
    if (imageFile) {
      await handleImageUpload(imageFile);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  // 제출
  const handleSubmit = async () => {
    if (!message.trim() || loading || disabled) return;
    
    setLoading(true);
    try {
      const response = await advancedChatWithAI({
        workspaceId,
        message: message.trim(),
        mode,
        contexts: contexts.length > 0 ? contexts : undefined,
        history: history.length > 0 ? history : undefined,
        currentFile,
        currentContent: fileContent,
        currentSelection: selection,
      });
      
      // 히스토리 업데이트
      setHistory((prev) => [
        ...prev,
        { role: "user", content: message.trim() },
        { role: "assistant", content: response.response },
      ]);
      
      onResponse(response);
      setMessage("");
      setContexts([]);
    } catch (err) {
      onError(err instanceof Error ? err.message : "요청 실패");
    } finally {
      setLoading(false);
    }
  };

  const modeConfig = MODE_CONFIG[mode];

  return (
    <div
      style={{
        borderTop: "1px solid #eee",
        padding: "12px",
        backgroundColor: "#fafafa",
      }}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
    >
      {/* 모드 선택 탭 */}
      <div style={{ display: "flex", gap: "4px", marginBottom: "12px" }}>
        {(Object.entries(MODE_CONFIG) as [AIMode, typeof modeConfig][]).map(([modeKey, config]) => (
          <button
            key={modeKey}
            onClick={() => setMode(modeKey)}
            style={{
              padding: "6px 12px",
              fontSize: "12px",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              backgroundColor: mode === modeKey ? config.color : "#e5e5e5",
              color: mode === modeKey ? "white" : "#666",
              fontWeight: mode === modeKey ? 600 : 400,
              transition: "all 0.15s",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            <span>{config.icon}</span>
            <span>{config.label}</span>
          </button>
        ))}
      </div>

      {/* 추가된 컨텍스트 표시 */}
      {contexts.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "10px" }}>
          {contexts.map((ctx, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "4px",
                padding: "4px 8px",
                backgroundColor: "#e3f2fd",
                borderRadius: "4px",
                fontSize: "12px",
              }}
            >
              <span>
                {ctx.type === "file" && "📄"}
                {ctx.type === "folder" && "📁"}
                {ctx.type === "image" && "🖼️"}
                {ctx.type === "clipboard" && "📋"}
                {ctx.type === "selection" && "✂️"}
              </span>
              <span style={{ maxWidth: "150px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {ctx.name || ctx.path || "context"}
              </span>
              <button
                onClick={() => removeContext(i)}
                style={{
                  padding: "0 4px",
                  border: "none",
                  background: "none",
                  cursor: "pointer",
                  fontSize: "14px",
                  color: "#666",
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 입력 영역 */}
      <div style={{ position: "relative" }}>
        <textarea
          ref={textareaRef}
          value={message}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder={modeConfig.placeholder}
          disabled={loading || disabled}
          style={{
            width: "100%",
            padding: "12px",
            paddingRight: "80px",
            fontSize: "14px",
            border: `2px solid ${loading ? "#ccc" : modeConfig.color}`,
            borderRadius: "8px",
            resize: "none",
            minHeight: "48px",
            maxHeight: "200px",
            outline: "none",
            boxSizing: "border-box",
            fontFamily: "inherit",
            lineHeight: "1.5",
          }}
        />

        {/* 버튼 그룹 */}
        <div
          style={{
            position: "absolute",
            right: "8px",
            bottom: "8px",
            display: "flex",
            gap: "4px",
          }}
        >
          {/* 이미지 업로드 버튼 */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadingImage}
            style={{
              padding: "6px",
              border: "none",
              borderRadius: "4px",
              backgroundColor: "#f0f0f0",
              cursor: "pointer",
              fontSize: "16px",
            }}
            title="이미지 첨부 (Ctrl+V로 붙여넣기 가능)"
          >
            {uploadingImage ? "⏳" : "🖼️"}
          </button>
          
          {/* 컨텍스트 추가 버튼 */}
          <button
            onClick={() => {
              setMessage((prev) => prev + "@");
              textareaRef.current?.focus();
            }}
            style={{
              padding: "6px",
              border: "none",
              borderRadius: "4px",
              backgroundColor: "#f0f0f0",
              cursor: "pointer",
              fontSize: "16px",
            }}
            title="컨텍스트 추가 (@)"
          >
            @
          </button>
          
          {/* 전송 버튼 */}
          <button
            onClick={handleSubmit}
            disabled={loading || disabled || !message.trim()}
            style={{
              padding: "6px 12px",
              border: "none",
              borderRadius: "4px",
              backgroundColor: loading || !message.trim() ? "#ccc" : modeConfig.color,
              color: "white",
              cursor: loading || !message.trim() ? "not-allowed" : "pointer",
              fontSize: "14px",
              fontWeight: 500,
            }}
          >
            {loading ? "..." : "→"}
          </button>
        </div>

        {/* 자동완성 드롭다운 */}
        {showSuggestions && suggestions.length > 0 && (
          <div
            ref={suggestionsRef}
            style={{
              position: "absolute",
              bottom: "100%",
              left: 0,
              right: 0,
              marginBottom: "4px",
              backgroundColor: "white",
              border: "1px solid #ddd",
              borderRadius: "8px",
              boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
              maxHeight: "200px",
              overflowY: "auto",
              zIndex: 100,
            }}
          >
            {suggestions.map((suggestion, i) => (
              <div
                key={i}
                onClick={() => selectSuggestion(suggestion)}
                style={{
                  padding: "10px 12px",
                  cursor: "pointer",
                  backgroundColor: i === selectedSuggestionIndex ? "#e3f2fd" : "white",
                  borderBottom: i < suggestions.length - 1 ? "1px solid #eee" : "none",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <span style={{ fontSize: "16px" }}>
                  {suggestion.type === "file" && "📄"}
                  {suggestion.type === "folder" && "📁"}
                </span>
                <div>
                  <div style={{ fontWeight: 500, fontSize: "13px" }}>{suggestion.name}</div>
                  {suggestion.path && (
                    <div style={{ fontSize: "11px", color: "#888" }}>{suggestion.path}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 숨겨진 파일 입력 */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileSelect}
        style={{ display: "none" }}
      />

      {/* 안내 텍스트 */}
      <div style={{ marginTop: "8px", fontSize: "11px", color: "#888", display: "flex", gap: "16px" }}>
        <span>💡 <strong>@</strong>로 파일 추가</span>
        <span>🖼️ <strong>Ctrl+V</strong>로 이미지 붙여넣기</span>
        <span>↵ <strong>Enter</strong>로 전송</span>
      </div>
    </div>
  );
}
