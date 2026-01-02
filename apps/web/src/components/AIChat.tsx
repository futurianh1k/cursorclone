"use client";

import { useState } from "react";
import { rewriteCode, validatePatch, applyPatch, chatWithAI, AIRewriteRequest, AIChatRequest } from "@/lib/api";

interface AIChatProps {
  workspaceId: string;
  currentFile?: string;
  fileContent?: string;
  selection?: { startLine: number; endLine: number };
}

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function AIChat({
  workspaceId,
  currentFile,
  fileContent,
  selection,
}: AIChatProps) {
  const [instruction, setInstruction] = useState("");
  const [loading, setLoading] = useState(false);
  const [diff, setDiff] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [mode, setMode] = useState<"chat" | "rewrite">("chat");

  const handleChat = async () => {
    if (!instruction.trim()) return;
    
    const userMessage = instruction.trim();
    setMessages([...messages, { role: "user", content: userMessage }]);
    setInstruction("");
    
    try {
      setLoading(true);
      setError(null);
      
      // 새로운 chatWithAI API 사용 - 파일 유무와 관계없이 동작
      const request: AIChatRequest = {
        workspaceId,
        message: userMessage,
        filePath: currentFile,
        fileContent: fileContent,
        selection: selection,
        history: messages.map(m => ({ role: m.role, content: m.content })),
      };
      
      const response = await chatWithAI(request);
      
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.response },
      ]);
      
      // Rewrite가 제안된 경우 사용자에게 알림
      if (response.suggestedAction === "rewrite" && currentFile && selection) {
        setMessages((prev) => [
          ...prev,
          { 
            role: "assistant", 
            content: "💡 코드 수정을 원하시면 **Rewrite** 모드로 전환해주세요." 
          },
        ]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get response");
    } finally {
      setLoading(false);
    }
  };

  const handleRewrite = async () => {
    if (!instruction.trim() || !currentFile || !selection) {
      setError("파일과 선택 영역을 지정해주세요.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setDiff(null);

      const request: AIRewriteRequest = {
        workspaceId,
        instruction: instruction.trim(),
        target: {
          file: currentFile,
          selection: {
            startLine: selection.startLine,
            endLine: selection.endLine,
          },
        },
      };

      const response = await rewriteCode(request);
      setDiff(response.diff);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rewrite code");
    } finally {
      setLoading(false);
    }
  };
  
  const handleSubmit = () => {
    if (mode === "chat") {
      handleChat();
    } else {
      handleRewrite();
    }
  };

  const handleApplyPatch = async () => {
    if (!diff) return;

    try {
      setApplying(true);
      setError(null);

      // 1. 패치 검증
      const validation = await validatePatch({
        workspaceId,
        patch: diff,
      });

      if (!validation.valid) {
        setError(`Invalid patch: ${validation.reason}`);
        return;
      }

      // 2. 패치 적용
      const result = await applyPatch({
        workspaceId,
        patch: diff,
        dryRun: false,
      });

      if (result.success) {
        setDiff(null);
        setInstruction("");
        alert(`패치가 적용되었습니다: ${result.appliedFiles.join(", ")}`);
        // TODO: 파일 트리 새로고침 및 파일 내용 다시 로드
      } else {
        setError(result.message || "Failed to apply patch");
      }
    } catch (err: any) {
      if (err.message?.includes("Conflict")) {
        setError("충돌이 발생했습니다. 파일이 변경되었을 수 있습니다.");
      } else {
        setError(err.message || "Failed to apply patch");
      }
    } finally {
      setApplying(false);
    }
  };

  const handleCancel = () => {
    setDiff(null);
    setError(null);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ padding: "12px", borderBottom: "1px solid #ddd" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
          <h3 style={{ margin: 0, fontSize: "16px" }}>AI Chat</h3>
          <div style={{ display: "flex", gap: "4px" }}>
            <button
              onClick={() => setMode("chat")}
              style={{
                padding: "4px 8px",
                fontSize: "11px",
                backgroundColor: mode === "chat" ? "#007acc" : "#f0f0f0",
                color: mode === "chat" ? "white" : "#333",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              Chat
            </button>
            <button
              onClick={() => setMode("rewrite")}
              style={{
                padding: "4px 8px",
                fontSize: "11px",
                backgroundColor: mode === "rewrite" ? "#007acc" : "#f0f0f0",
                color: mode === "rewrite" ? "white" : "#333",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              Rewrite
            </button>
          </div>
        </div>
        {currentFile && (
          <div style={{ fontSize: "11px", color: "#666" }}>
            📄 {currentFile}
            {selection && ` (lines ${selection.startLine}-${selection.endLine})`}
          </div>
        )}
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "12px" }}>
        {/* 메시지 목록 */}
        {messages.length > 0 && (
          <div style={{ marginBottom: "12px" }}>
            {messages.map((msg, i) => (
              <div
                key={i}
                style={{
                  marginBottom: "8px",
                  padding: "8px",
                  backgroundColor: msg.role === "user" ? "#e3f2fd" : "#f5f5f5",
                  borderRadius: "8px",
                  fontSize: "13px",
                }}
              >
                <div style={{ fontSize: "10px", color: "#666", marginBottom: "4px" }}>
                  {msg.role === "user" ? "You" : "AI"}
                </div>
                <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>
              </div>
            ))}
          </div>
        )}
        
        {!diff ? (
          <div>
            <textarea
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              placeholder={mode === "chat" ? "질문을 입력하세요... (Enter로 전송)" : "코드 수정 지시사항을 입력하세요..."}
              style={{
                width: "100%",
                minHeight: "80px",
                padding: "8px",
                fontSize: "13px",
                border: "1px solid #ddd",
                borderRadius: "4px",
                resize: "vertical",
                fontFamily: "inherit",
              }}
              disabled={loading || (mode === "rewrite" && (!currentFile || !selection))}
            />
            <button
              onClick={handleSubmit}
              disabled={loading || !instruction.trim() || (mode === "rewrite" && (!currentFile || !selection))}
              style={{
                marginTop: "8px",
                padding: "8px 16px",
                fontSize: "13px",
                backgroundColor: loading ? "#ccc" : "#007acc",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: loading ? "not-allowed" : "pointer",
                width: "100%",
              }}
            >
              {loading ? "처리 중..." : mode === "chat" ? "질문하기" : "코드 수정"}
            </button>
            {mode === "rewrite" && (!currentFile || !selection) && (
              <div style={{ marginTop: "8px", fontSize: "11px", color: "#666" }}>
                💡 코드 수정을 하려면 파일을 열고 코드 영역을 선택하세요.
              </div>
            )}
          </div>
        ) : (
          <div>
            <div style={{ fontSize: "12px", fontWeight: "bold", marginBottom: "8px" }}>
              Diff Preview
            </div>
            <pre
              style={{
                fontSize: "11px",
                padding: "8px",
                backgroundColor: "#f5f5f5",
                border: "1px solid #ddd",
                borderRadius: "4px",
                overflow: "auto",
                maxHeight: "300px",
                whiteSpace: "pre-wrap",
                fontFamily: "monospace",
              }}
            >
              {diff}
            </pre>
            <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
              <button
                onClick={handleApplyPatch}
                disabled={applying}
                style={{
                  flex: 1,
                  padding: "8px 16px",
                  fontSize: "13px",
                  backgroundColor: applying ? "#ccc" : "#28a745",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: applying ? "not-allowed" : "pointer",
                }}
              >
                {applying ? "적용 중..." : "적용"}
              </button>
              <button
                onClick={handleCancel}
                disabled={applying}
                style={{
                  flex: 1,
                  padding: "8px 16px",
                  fontSize: "13px",
                  backgroundColor: "#6c757d",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: applying ? "not-allowed" : "pointer",
                }}
              >
                취소
              </button>
            </div>
          </div>
        )}

        {error && (
          <div
            style={{
              marginTop: "12px",
              padding: "8px",
              fontSize: "12px",
              color: "#d32f2f",
              backgroundColor: "#ffebee",
              border: "1px solid #ffcdd2",
              borderRadius: "4px",
            }}
          >
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
