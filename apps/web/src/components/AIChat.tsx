"use client";

import { useState, useRef, useEffect } from "react";
import { rewriteCode, validatePatch, applyPatch, chatWithAI, AIRewriteRequest, AIChatRequest } from "@/lib/api";
import { createPlan, runAgent, debugCode, AIPlanRequest, AIAgentRequest, AIDebugRequest } from "@/lib/api";

interface AIChatProps {
  workspaceId: string;
  currentFile?: string;
  fileContent?: string;
  selection?: { startLine: number; endLine: number };
}

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  type?: "plan" | "agent" | "debug" | "chat";
}

type AIMode = "ask" | "agent" | "plan" | "debug";

const MODE_INFO: Record<AIMode, { name: string; icon: string; description: string; color: string }> = {
  ask: {
    name: "Ask",
    icon: "💬",
    description: "코드에 대해 질문하고 답변을 받습니다.",
    color: "#007acc",
  },
  agent: {
    name: "Agent",
    icon: "🤖",
    description: "자동으로 코드를 분석하고 변경 사항을 제안합니다.",
    color: "#7c3aed",
  },
  plan: {
    name: "Plan",
    icon: "📋",
    description: "목표를 분석하고 단계별 실행 계획을 생성합니다.",
    color: "#059669",
  },
  debug: {
    name: "Debug",
    icon: "🐛",
    description: "에러를 분석하고 버그 수정 방안을 제시합니다.",
    color: "#dc2626",
  },
};

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
  const [mode, setMode] = useState<AIMode>("ask");
  const [showRewrite, setShowRewrite] = useState(false);
  
  // 자동 스크롤을 위한 ref
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  
  // 메시지가 추가될 때 자동 스크롤
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // ============================================================
  // Ask Mode (Chat)
  // ============================================================
  const handleAsk = async () => {
    if (!instruction.trim()) return;
    
    const userMessage = instruction.trim();
    setMessages([...messages, { role: "user", content: userMessage }]);
    setInstruction("");
    
    try {
      setLoading(true);
      setError(null);
      
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
        { role: "assistant", content: response.response, type: "chat" },
      ]);
      
      // Rewrite가 제안된 경우
      if (response.suggestedAction === "rewrite" && currentFile && selection) {
        setShowRewrite(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get response");
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // Plan Mode
  // ============================================================
  const handlePlan = async () => {
    if (!instruction.trim()) return;
    
    const goal = instruction.trim();
    setMessages([...messages, { role: "user", content: `📋 목표: ${goal}` }]);
    setInstruction("");
    
    try {
      setLoading(true);
      setError(null);
      
      const request: AIPlanRequest = {
        workspaceId,
        goal,
        context: currentFile ? `현재 파일: ${currentFile}` : undefined,
        filePaths: currentFile ? [currentFile] : undefined,
      };
      
      const response = await createPlan(request);
      
      // 계획을 보기 좋게 포맷팅
      let planContent = `## ${response.summary}\n\n`;
      planContent += `**예상 변경 파일**: ${response.estimatedChanges}개\n\n`;
      planContent += `### 실행 단계\n`;
      response.steps.forEach((step) => {
        planContent += `\n${step.stepNumber}. ${step.description}`;
        if (step.filePath) {
          planContent += `\n   📄 \`${step.filePath}\``;
        }
      });
      
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: planContent, type: "plan" },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create plan");
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // Agent Mode
  // ============================================================
  const handleAgent = async () => {
    if (!instruction.trim()) return;
    
    const agentInstruction = instruction.trim();
    setMessages([...messages, { role: "user", content: `🤖 지시: ${agentInstruction}` }]);
    setInstruction("");
    
    try {
      setLoading(true);
      setError(null);
      
      const request: AIAgentRequest = {
        workspaceId,
        instruction: agentInstruction,
        filePaths: currentFile ? [currentFile] : undefined,
        autoApply: false,
      };
      
      const response = await runAgent(request);
      
      // 에이전트 응답 포맷팅
      let agentContent = `## ${response.summary}\n\n`;
      
      if (response.changes.length > 0) {
        agentContent += `### 변경 사항 (${response.changes.length}개)\n`;
        response.changes.forEach((change, i) => {
          agentContent += `\n**${i + 1}. ${change.filePath}** (${change.action})\n`;
          agentContent += `${change.description}\n`;
          if (change.diff) {
            agentContent += `\`\`\`diff\n${change.diff}\n\`\`\`\n`;
          }
        });
        
        // diff가 있으면 저장
        const firstDiff = response.changes.find(c => c.diff);
        if (firstDiff?.diff) {
          setDiff(firstDiff.diff);
        }
      } else {
        agentContent += `변경 사항이 없습니다.`;
      }
      
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: agentContent, type: "agent" },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run agent");
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // Debug Mode
  // ============================================================
  const handleDebug = async () => {
    if (!instruction.trim()) return;
    
    const debugInput = instruction.trim();
    setMessages([...messages, { role: "user", content: `🐛 디버그: ${debugInput}` }]);
    setInstruction("");
    
    try {
      setLoading(true);
      setError(null);
      
      // 에러 메시지와 설명 분리 (첫 줄이 에러, 나머지가 설명)
      const lines = debugInput.split('\n');
      const errorMessage = lines[0];
      const description = lines.slice(1).join('\n') || undefined;
      
      const request: AIDebugRequest = {
        workspaceId,
        errorMessage,
        description,
        filePath: currentFile,
        fileContent: fileContent,
      };
      
      const response = await debugCode(request);
      
      // 디버그 응답 포맷팅
      let debugContent = `## 🔍 문제 진단\n\n`;
      debugContent += `${response.diagnosis}\n\n`;
      debugContent += `### 근본 원인\n${response.rootCause}\n\n`;
      
      if (response.fixes && response.fixes.length > 0) {
        debugContent += `### 수정 제안 (${response.fixes.length}개)\n`;
        response.fixes.forEach((fix, i) => {
          debugContent += `\n**${i + 1}. ${fix.filePath}**`;
          if (fix.lineNumber) debugContent += ` (line ${fix.lineNumber})`;
          debugContent += `\n`;
          debugContent += `${fix.explanation}\n`;
          if (fix.originalCode && fix.fixedCode) {
            debugContent += `\n\`\`\`diff\n- ${fix.originalCode}\n+ ${fix.fixedCode}\n\`\`\`\n`;
          }
        });
      }
      
      if (response.preventionTips && response.preventionTips.length > 0) {
        debugContent += `\n### 💡 예방 팁\n`;
        response.preventionTips.forEach((tip) => {
          debugContent += `- ${tip}\n`;
        });
      }
      
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: debugContent, type: "debug" },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to debug");
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // Rewrite (Code Modification)
  // ============================================================
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
      setShowRewrite(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rewrite code");
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // Submit Handler (mode-based)
  // ============================================================
  const handleSubmit = () => {
    switch (mode) {
      case "ask":
        handleAsk();
        break;
      case "plan":
        handlePlan();
        break;
      case "agent":
        handleAgent();
        break;
      case "debug":
        handleDebug();
        break;
    }
  };

  // ============================================================
  // Patch Application
  // ============================================================
  const handleApplyPatch = async () => {
    if (!diff) return;

    try {
      setApplying(true);
      setError(null);

      const validation = await validatePatch({
        workspaceId,
        patch: diff,
      });

      if (!validation.valid) {
        setError(`Invalid patch: ${validation.reason}`);
        return;
      }

      const result = await applyPatch({
        workspaceId,
        patch: diff,
        dryRun: false,
      });

      if (result.success) {
        setDiff(null);
        setInstruction("");
        setMessages((prev) => [
          ...prev,
          { role: "system", content: `✅ 패치 적용 완료: ${result.appliedFiles.join(", ")}` },
        ]);
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

  const getPlaceholder = () => {
    switch (mode) {
      case "ask":
        return "코드에 대해 질문하세요... (Enter로 전송)";
      case "plan":
        return "달성할 목표를 입력하세요... (예: 로그인 기능 추가)";
      case "agent":
        return "수행할 작업을 지시하세요... (예: 모든 함수에 docstring 추가)";
      case "debug":
        return "에러 메시지를 붙여넣으세요...";
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* 헤더 - 모드 선택 */}
      <div style={{ flexShrink: 0, padding: "12px", borderBottom: "1px solid #ddd", backgroundColor: "#fafafa" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
          <h3 style={{ margin: 0, fontSize: "16px" }}>
            {MODE_INFO[mode].icon} {MODE_INFO[mode].name}
          </h3>
        </div>
        
        {/* 모드 선택 탭 */}
        <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
          {(Object.keys(MODE_INFO) as AIMode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              style={{
                padding: "6px 12px",
                fontSize: "12px",
                backgroundColor: mode === m ? MODE_INFO[m].color : "#f0f0f0",
                color: mode === m ? "white" : "#555",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "4px",
                transition: "all 0.2s",
              }}
              title={MODE_INFO[m].description}
            >
              <span>{MODE_INFO[m].icon}</span>
              <span>{MODE_INFO[m].name}</span>
            </button>
          ))}
        </div>
        
        {/* 모드 설명 */}
        <div style={{ fontSize: "11px", color: "#666", marginTop: "8px" }}>
          {MODE_INFO[mode].description}
        </div>
        
        {/* 현재 파일 정보 */}
        {currentFile && (
          <div style={{ fontSize: "11px", color: "#888", marginTop: "4px" }}>
            📄 {currentFile}
            {selection && ` (lines ${selection.startLine}-${selection.endLine})`}
          </div>
        )}
      </div>

      {/* 메시지 영역 - 스크롤 가능 */}
      <div 
        ref={messagesContainerRef}
        style={{ 
          flex: "1 1 0",
          minHeight: 0,
          overflowY: "auto", 
          padding: "12px",
          backgroundColor: "#fff",
        }}
      >
        {/* 빈 상태 메시지 */}
        {messages.length === 0 && !loading && (
          <div style={{ 
            height: "100%",
            display: "flex", 
            flexDirection: "column",
            alignItems: "center", 
            justifyContent: "center",
            color: "#999",
            fontSize: "13px",
            textAlign: "center",
            gap: "8px",
          }}>
            <span style={{ fontSize: "32px" }}>{MODE_INFO[mode].icon}</span>
            <span>{MODE_INFO[mode].description}</span>
          </div>
        )}
        
        {/* 메시지 목록 */}
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              marginBottom: "12px",
              padding: "10px 12px",
              backgroundColor: msg.role === "user" ? "#e3f2fd" : 
                              msg.role === "system" ? "#e8f5e9" : "#f5f5f5",
              borderRadius: "12px",
              fontSize: "13px",
              maxWidth: msg.role === "user" ? "85%" : "95%",
              marginLeft: msg.role === "user" ? "auto" : "0",
              marginRight: msg.role === "user" ? "0" : "auto",
              boxShadow: "0 1px 2px rgba(0,0,0,0.1)",
              borderLeft: msg.type ? `3px solid ${MODE_INFO[msg.type as AIMode]?.color || '#007acc'}` : undefined,
            }}
          >
            <div style={{ fontSize: "10px", color: "#666", marginBottom: "4px", fontWeight: 500 }}>
              {msg.role === "user" ? "👤 You" : msg.role === "system" ? "⚙️ System" : "🤖 AI"}
              {msg.type && ` (${MODE_INFO[msg.type as AIMode]?.name || msg.type})`}
            </div>
            <div style={{ whiteSpace: "pre-wrap", lineHeight: "1.5" }}>{msg.content}</div>
          </div>
        ))}
        
        {/* 로딩 인디케이터 */}
        {loading && (
          <div style={{
            padding: "10px 12px",
            backgroundColor: "#f5f5f5",
            borderRadius: "12px",
            fontSize: "13px",
            maxWidth: "90%",
            marginBottom: "12px",
            borderLeft: `3px solid ${MODE_INFO[mode].color}`,
          }}>
            <div style={{ fontSize: "10px", color: "#666", marginBottom: "4px", fontWeight: 500 }}>
              🤖 AI ({MODE_INFO[mode].name})
            </div>
            <div style={{ color: "#666" }}>⏳ 처리 중...</div>
          </div>
        )}
        
        {/* 자동 스크롤 앵커 */}
        <div ref={messagesEndRef} />
      </div>

      {/* 입력 영역 - 하단 고정 */}
      <div style={{ flexShrink: 0, padding: "12px", borderTop: "1px solid #eee", backgroundColor: "#fafafa" }}>
        {!diff ? (
          <div>
            {/* Rewrite 모드 토글 (Agent 모드에서 코드 수정 시) */}
            {showRewrite && currentFile && selection && (
              <div style={{ 
                marginBottom: "8px", 
                padding: "8px", 
                backgroundColor: "#fff3cd", 
                borderRadius: "6px",
                fontSize: "12px",
              }}>
                💡 코드 수정을 원하시나요?{" "}
                <button
                  onClick={() => { setShowRewrite(false); handleRewrite(); }}
                  style={{
                    padding: "2px 8px",
                    backgroundColor: "#007acc",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                    fontSize: "11px",
                  }}
                >
                  Rewrite 실행
                </button>
              </div>
            )}
            
            <textarea
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              placeholder={getPlaceholder()}
              style={{
                width: "100%",
                minHeight: mode === "debug" ? "80px" : "60px",
                padding: "10px",
                fontSize: "13px",
                border: `2px solid ${MODE_INFO[mode].color}20`,
                borderRadius: "8px",
                resize: "none",
                fontFamily: "inherit",
                boxSizing: "border-box",
                outline: "none",
              }}
              disabled={loading}
            />
            <button
              onClick={handleSubmit}
              disabled={loading || !instruction.trim()}
              style={{
                marginTop: "8px",
                padding: "10px 16px",
                fontSize: "13px",
                backgroundColor: (loading || !instruction.trim()) ? "#ccc" : MODE_INFO[mode].color,
                color: "white",
                border: "none",
                borderRadius: "8px",
                cursor: (loading || !instruction.trim()) ? "not-allowed" : "pointer",
                width: "100%",
                fontWeight: 500,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "6px",
              }}
            >
              {loading ? "⏳ 처리 중..." : (
                <>
                  <span>{MODE_INFO[mode].icon}</span>
                  <span>
                    {mode === "ask" && "질문하기"}
                    {mode === "plan" && "계획 생성"}
                    {mode === "agent" && "실행하기"}
                    {mode === "debug" && "분석하기"}
                  </span>
                </>
              )}
            </button>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: "12px", fontWeight: "bold", marginBottom: "8px" }}>
              📝 Diff Preview
            </div>
            <pre
              style={{
                fontSize: "11px",
                padding: "8px",
                backgroundColor: "#f5f5f5",
                border: "1px solid #ddd",
                borderRadius: "4px",
                overflow: "auto",
                maxHeight: "200px",
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
                {applying ? "적용 중..." : "✅ 적용"}
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
                ❌ 취소
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
            ⚠️ {error}
          </div>
        )}
      </div>
    </div>
  );
}
