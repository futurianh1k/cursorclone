"use client";

import { useState, useEffect } from "react";
import {
  getSSHConnectionInfo,
  setupSSHKey,
  generateSSHKeyPair,
  getCursorSSHCommand,
  SSHConnectionResponse,
  CursorSSHCommandResponse,
} from "@/lib/api";

interface SSHConnectionPanelProps {
  workspaceId: string;
}

export default function SSHConnectionPanel({ workspaceId }: SSHConnectionPanelProps) {
  const [sshInfo, setSSHInfo] = useState<SSHConnectionResponse | null>(null);
  const [cursorCommand, setCursorCommand] = useState<CursorSSHCommandResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"connect" | "key" | "config">("connect");
  
  // SSH 키 설정 상태
  const [publicKey, setPublicKey] = useState("");
  const [keyLoading, setKeyLoading] = useState(false);
  const [keyMessage, setKeyMessage] = useState<string | null>(null);
  
  // 키 생성 결과
  const [generatedKey, setGeneratedKey] = useState<{ publicKey: string; privateKey: string } | null>(null);

  useEffect(() => {
    loadSSHInfo();
  }, [workspaceId]);

  const loadSSHInfo = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [info, command] = await Promise.all([
        getSSHConnectionInfo(workspaceId),
        getCursorSSHCommand(workspaceId),
      ]);
      
      setSSHInfo(info);
      setCursorCommand(command);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load SSH info");
    } finally {
      setLoading(false);
    }
  };

  const handleSetupKey = async () => {
    if (!publicKey.trim()) {
      setKeyMessage("SSH 공개키를 입력하세요.");
      return;
    }
    
    try {
      setKeyLoading(true);
      setKeyMessage(null);
      
      const result = await setupSSHKey(workspaceId, publicKey);
      setKeyMessage(`✅ ${result.message}${result.fingerprint ? ` (${result.fingerprint})` : ""}`);
      setPublicKey("");
    } catch (err) {
      setKeyMessage(`❌ ${err instanceof Error ? err.message : "Failed to setup SSH key"}`);
    } finally {
      setKeyLoading(false);
    }
  };

  const handleGenerateKey = async () => {
    try {
      setKeyLoading(true);
      setKeyMessage(null);
      setGeneratedKey(null);
      
      const result = await generateSSHKeyPair(workspaceId, "ed25519");
      setGeneratedKey({
        publicKey: result.publicKey,
        privateKey: result.privateKey,
      });
      setKeyMessage(`✅ SSH 키 쌍 생성 완료 (${result.fingerprint}). 개인키를 안전하게 저장하세요!`);
    } catch (err) {
      setKeyMessage(`❌ ${err instanceof Error ? err.message : "Failed to generate SSH key"}`);
    } finally {
      setKeyLoading(false);
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    alert(`${label} 복사됨!`);
  };

  if (loading) {
    return (
      <div style={{ padding: "20px", textAlign: "center", color: "#666" }}>
        ⏳ SSH 연결 정보 로딩 중...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "20px", color: "#d32f2f", backgroundColor: "#ffebee", borderRadius: "8px" }}>
        ❌ {error}
        <button onClick={loadSSHInfo} style={{ marginLeft: "10px", cursor: "pointer" }}>
          재시도
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: "16px", fontFamily: "system-ui, -apple-system, sans-serif" }}>
      <h3 style={{ margin: "0 0 16px", fontSize: "18px", display: "flex", alignItems: "center", gap: "8px" }}>
        🔐 SSH 접속
        {sshInfo && (
          <span style={{
            fontSize: "12px",
            padding: "2px 8px",
            borderRadius: "12px",
            backgroundColor: sshInfo.status === "available" ? "#e8f5e9" : "#ffebee",
            color: sshInfo.status === "available" ? "#2e7d32" : "#c62828",
          }}>
            {sshInfo.status === "available" ? "🟢 사용 가능" : "🔴 사용 불가"}
          </span>
        )}
      </h3>

      {/* 탭 */}
      <div style={{ display: "flex", gap: "4px", marginBottom: "16px", borderBottom: "1px solid #ddd" }}>
        {[
          { id: "connect", label: "🔗 연결하기" },
          { id: "key", label: "🔑 SSH 키 설정" },
          { id: "config", label: "⚙️ SSH 설정" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            style={{
              padding: "10px 16px",
              fontSize: "13px",
              backgroundColor: activeTab === tab.id ? "#007acc" : "transparent",
              color: activeTab === tab.id ? "white" : "#333",
              border: "none",
              borderRadius: "8px 8px 0 0",
              cursor: "pointer",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 탭 내용 */}
      {activeTab === "connect" && sshInfo && cursorCommand && (
        <div>
          {/* 연결 정보 */}
          <div style={{ backgroundColor: "#f5f5f5", padding: "12px", borderRadius: "8px", marginBottom: "16px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "13px" }}>
              <div><strong>호스트:</strong> {sshInfo.connection.host}</div>
              <div><strong>포트:</strong> {sshInfo.connection.port}</div>
              <div><strong>사용자:</strong> {sshInfo.connection.username}</div>
              <div><strong>인증:</strong> {sshInfo.connection.authType === "key" ? "SSH 키" : "비밀번호"}</div>
            </div>
          </div>

          {/* SSH 명령어 */}
          <div style={{ marginBottom: "16px" }}>
            <label style={{ fontSize: "12px", color: "#666", display: "block", marginBottom: "4px" }}>
              터미널 SSH 접속 명령어
            </label>
            <div style={{ display: "flex", gap: "8px" }}>
              <input
                type="text"
                value={sshInfo.sshCommand}
                readOnly
                style={{
                  flex: 1,
                  padding: "10px",
                  fontSize: "13px",
                  fontFamily: "monospace",
                  border: "1px solid #ddd",
                  borderRadius: "6px",
                  backgroundColor: "#fafafa",
                }}
              />
              <button
                onClick={() => copyToClipboard(sshInfo.sshCommand, "SSH 명령어")}
                style={{
                  padding: "10px 16px",
                  backgroundColor: "#007acc",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                }}
              >
                📋 복사
              </button>
            </div>
          </div>

          {/* Cursor/VS Code 접속 */}
          <div style={{ marginBottom: "16px" }}>
            <label style={{ fontSize: "12px", color: "#666", display: "block", marginBottom: "4px" }}>
              Cursor / VS Code Remote SSH
            </label>
            <a
              href={sshInfo.vscodeRemoteUri}
              style={{
                display: "inline-block",
                padding: "10px 20px",
                backgroundColor: "#7c3aed",
                color: "white",
                textDecoration: "none",
                borderRadius: "6px",
                fontSize: "13px",
              }}
            >
              🚀 Cursor에서 열기
            </a>
          </div>

          {/* 접속 방법 안내 */}
          <div style={{ backgroundColor: "#e3f2fd", padding: "12px", borderRadius: "8px", fontSize: "13px" }}>
            <strong>📝 Cursor Remote SSH 접속 방법:</strong>
            <ol style={{ margin: "8px 0 0", paddingLeft: "20px" }}>
              <li>{cursorCommand.instructions.step1}</li>
              <li>{cursorCommand.instructions.step2}</li>
              <li>{cursorCommand.instructions.step3}</li>
            </ol>
          </div>
        </div>
      )}

      {activeTab === "key" && (
        <div>
          {/* 기존 키 설정 */}
          <div style={{ marginBottom: "20px" }}>
            <label style={{ fontSize: "14px", fontWeight: 500, display: "block", marginBottom: "8px" }}>
              🔑 SSH 공개키 등록
            </label>
            <p style={{ fontSize: "12px", color: "#666", marginBottom: "8px" }}>
              기존에 생성한 SSH 공개키를 등록하세요. (예: ~/.ssh/id_ed25519.pub)
            </p>
            <textarea
              value={publicKey}
              onChange={(e) => setPublicKey(e.target.value)}
              placeholder="ssh-ed25519 AAAA... user@example.com"
              style={{
                width: "100%",
                minHeight: "80px",
                padding: "10px",
                fontSize: "12px",
                fontFamily: "monospace",
                border: "1px solid #ddd",
                borderRadius: "6px",
                resize: "vertical",
                boxSizing: "border-box",
              }}
            />
            <button
              onClick={handleSetupKey}
              disabled={keyLoading || !publicKey.trim()}
              style={{
                marginTop: "8px",
                padding: "10px 20px",
                backgroundColor: keyLoading || !publicKey.trim() ? "#ccc" : "#28a745",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: keyLoading || !publicKey.trim() ? "not-allowed" : "pointer",
              }}
            >
              {keyLoading ? "⏳ 설정 중..." : "✅ 공개키 등록"}
            </button>
          </div>

          <hr style={{ border: "none", borderTop: "1px solid #eee", margin: "20px 0" }} />

          {/* 키 생성 */}
          <div style={{ marginBottom: "20px" }}>
            <label style={{ fontSize: "14px", fontWeight: 500, display: "block", marginBottom: "8px" }}>
              🔐 새 SSH 키 쌍 생성
            </label>
            <p style={{ fontSize: "12px", color: "#666", marginBottom: "8px" }}>
              SSH 키가 없다면 새로 생성할 수 있습니다. 개인키는 반드시 안전하게 저장하세요.
            </p>
            <button
              onClick={handleGenerateKey}
              disabled={keyLoading}
              style={{
                padding: "10px 20px",
                backgroundColor: keyLoading ? "#ccc" : "#7c3aed",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: keyLoading ? "not-allowed" : "pointer",
              }}
            >
              {keyLoading ? "⏳ 생성 중..." : "🔑 SSH 키 쌍 생성 (Ed25519)"}
            </button>
          </div>

          {/* 생성된 키 표시 */}
          {generatedKey && (
            <div style={{ backgroundColor: "#fff3cd", padding: "12px", borderRadius: "8px", marginBottom: "16px" }}>
              <strong>⚠️ 개인키를 지금 저장하세요! (다시 볼 수 없습니다)</strong>
              
              <div style={{ marginTop: "12px" }}>
                <label style={{ fontSize: "12px", color: "#666" }}>공개키 (서버에 자동 등록됨)</label>
                <textarea
                  value={generatedKey.publicKey}
                  readOnly
                  style={{
                    width: "100%",
                    height: "60px",
                    padding: "8px",
                    fontSize: "11px",
                    fontFamily: "monospace",
                    border: "1px solid #ddd",
                    borderRadius: "4px",
                    marginTop: "4px",
                    boxSizing: "border-box",
                  }}
                />
              </div>
              
              <div style={{ marginTop: "12px" }}>
                <label style={{ fontSize: "12px", color: "#666" }}>개인키 (로컬에 저장: ~/.ssh/id_ed25519)</label>
                <textarea
                  value={generatedKey.privateKey}
                  readOnly
                  style={{
                    width: "100%",
                    height: "150px",
                    padding: "8px",
                    fontSize: "11px",
                    fontFamily: "monospace",
                    border: "1px solid #ddd",
                    borderRadius: "4px",
                    marginTop: "4px",
                    boxSizing: "border-box",
                  }}
                />
                <button
                  onClick={() => copyToClipboard(generatedKey.privateKey, "개인키")}
                  style={{
                    marginTop: "8px",
                    padding: "8px 16px",
                    backgroundColor: "#dc2626",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                  }}
                >
                  📋 개인키 복사
                </button>
              </div>
            </div>
          )}

          {/* 메시지 */}
          {keyMessage && (
            <div style={{
              padding: "10px",
              borderRadius: "6px",
              backgroundColor: keyMessage.startsWith("✅") ? "#e8f5e9" : "#ffebee",
              color: keyMessage.startsWith("✅") ? "#2e7d32" : "#c62828",
              fontSize: "13px",
            }}>
              {keyMessage}
            </div>
          )}
        </div>
      )}

      {activeTab === "config" && cursorCommand && (
        <div>
          <label style={{ fontSize: "14px", fontWeight: 500, display: "block", marginBottom: "8px" }}>
            📝 SSH Config 설정
          </label>
          <p style={{ fontSize: "12px", color: "#666", marginBottom: "8px" }}>
            ~/.ssh/config 파일에 다음 내용을 추가하세요:
          </p>
          <pre style={{
            padding: "12px",
            backgroundColor: "#1e1e1e",
            color: "#d4d4d4",
            borderRadius: "6px",
            fontSize: "12px",
            overflow: "auto",
            whiteSpace: "pre-wrap",
          }}>
            {cursorCommand.sshConfig.content}
          </pre>
          <button
            onClick={() => copyToClipboard(cursorCommand.sshConfig.content, "SSH 설정")}
            style={{
              marginTop: "8px",
              padding: "10px 16px",
              backgroundColor: "#007acc",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
            }}
          >
            📋 설정 복사
          </button>

          <div style={{ marginTop: "20px", backgroundColor: "#f5f5f5", padding: "12px", borderRadius: "8px", fontSize: "13px" }}>
            <strong>💡 사용 방법:</strong>
            <ol style={{ margin: "8px 0 0", paddingLeft: "20px" }}>
              <li>위 설정을 ~/.ssh/config에 추가</li>
              <li>터미널에서: <code>ssh cursor-{workspaceId}</code></li>
              <li>또는 Cursor에서: Remote SSH → Connect to Host → cursor-{workspaceId}</li>
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}
