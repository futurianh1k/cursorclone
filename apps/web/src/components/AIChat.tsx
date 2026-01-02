"use client";

import { useState } from "react";
import { rewriteCode, validatePatch, applyPatch, AIRewriteRequest } from "@/lib/api";

interface AIChatProps {
  workspaceId: string;
  currentFile?: string;
  selection?: { startLine: number; endLine: number };
}

export default function AIChat({
  workspaceId,
  currentFile,
  selection,
}: AIChatProps) {
  const [instruction, setInstruction] = useState("");
  const [loading, setLoading] = useState(false);
  const [diff, setDiff] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);

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
        <h3 style={{ margin: "0 0 8px 0", fontSize: "16px" }}>AI Chat</h3>
        {currentFile && selection && (
          <div style={{ fontSize: "11px", color: "#666", marginBottom: "8px" }}>
            {currentFile} (lines {selection.startLine}-{selection.endLine})
          </div>
        )}
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "12px" }}>
        {!diff ? (
          <div>
            <textarea
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="코드 수정 지시사항을 입력하세요..."
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
              disabled={loading || !currentFile || !selection}
            />
            <button
              onClick={handleRewrite}
              disabled={loading || !instruction.trim() || !currentFile || !selection}
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
              {loading ? "처리 중..." : "코드 수정"}
            </button>
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
