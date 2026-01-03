"use client";

/**
 * Web IDE 런처 컴포넌트
 * 브라우저 기반 VS Code (code-server)를 새 탭에서 실행
 */

import React, { useState } from "react";
import { getWorkspaceIDEUrl } from "../lib/api";

interface WebIDELauncherProps {
  workspaceId: string;
  workspaceName?: string;
  className?: string;
}

export function WebIDELauncher({
  workspaceId,
  workspaceName,
  className = "",
}: WebIDELauncherProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleOpenIDE = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await getWorkspaceIDEUrl(workspaceId);
      
      if (result.url) {
        // 새 탭에서 IDE 열기
        window.open(result.url, "_blank", "noopener,noreferrer");
      } else {
        setError("IDE URL을 가져올 수 없습니다.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "IDE 실행에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`web-ide-launcher ${className}`}>
      <button
        onClick={handleOpenIDE}
        disabled={loading}
        className="web-ide-button"
        title={`${workspaceName || workspaceId} 워크스페이스에서 Web IDE 열기`}
      >
        {loading ? (
          <>
            <span className="spinner" />
            IDE 실행 중...
          </>
        ) : (
          <>
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="m18 16 4-4-4-4" />
              <path d="m6 8-4 4 4 4" />
              <path d="m14.5 4-5 16" />
            </svg>
            Web IDE 열기
          </>
        )}
      </button>

      {error && (
        <div className="error-message">
          ⚠️ {error}
          <button onClick={() => setError(null)} className="dismiss-btn">
            ✕
          </button>
        </div>
      )}

      <style jsx>{`
        .web-ide-launcher {
          display: inline-block;
        }

        .web-ide-button {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 10px 20px;
          background: linear-gradient(135deg, #007acc 0%, #0098ff 100%);
          color: white;
          border: none;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow: 0 2px 8px rgba(0, 122, 204, 0.3);
        }

        .web-ide-button:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(0, 122, 204, 0.4);
        }

        .web-ide-button:active:not(:disabled) {
          transform: translateY(0);
        }

        .web-ide-button:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }

        .spinner {
          display: inline-block;
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-radius: 50%;
          border-top-color: white;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }

        .error-message {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 8px;
          padding: 8px 12px;
          background: rgba(220, 38, 38, 0.1);
          border: 1px solid rgba(220, 38, 38, 0.3);
          border-radius: 6px;
          color: #dc2626;
          font-size: 13px;
        }

        .dismiss-btn {
          margin-left: auto;
          padding: 2px 6px;
          background: transparent;
          border: none;
          color: #dc2626;
          cursor: pointer;
          opacity: 0.7;
        }

        .dismiss-btn:hover {
          opacity: 1;
        }
      `}</style>
    </div>
  );
}

/**
 * 큰 버전의 Web IDE 런처 (대시보드용)
 */
export function WebIDELauncherCard({
  workspaceId,
  workspaceName,
}: WebIDELauncherProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleOpenIDE = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await getWorkspaceIDEUrl(workspaceId);
      
      if (result.url) {
        window.open(result.url, "_blank", "noopener,noreferrer");
      } else {
        setError("IDE URL을 가져올 수 없습니다.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "IDE 실행에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="web-ide-card">
      <div className="card-header">
        <div className="ide-icon">
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="16 18 22 12 16 6" />
            <polyline points="8 6 2 12 8 18" />
          </svg>
        </div>
        <div className="card-title">
          <h3>Web IDE</h3>
          <p>브라우저에서 VS Code 실행</p>
        </div>
      </div>

      <div className="card-body">
        <ul className="feature-list">
          <li>✓ 풀 VS Code 환경</li>
          <li>✓ 터미널 & 디버거</li>
          <li>✓ AI 코딩 지원 (Tabby + Continue)</li>
          <li>✓ Git 통합</li>
        </ul>
      </div>

      <div className="card-footer">
        <button
          onClick={handleOpenIDE}
          disabled={loading}
          className="launch-button"
        >
          {loading ? (
            <>
              <span className="spinner" />
              시작 중...
            </>
          ) : (
            <>
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                <polyline points="15 3 21 3 21 9" />
                <line x1="10" y1="14" x2="21" y2="3" />
              </svg>
              IDE 열기
            </>
          )}
        </button>

        {error && <p className="error">{error}</p>}
      </div>

      <style jsx>{`
        .web-ide-card {
          background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
          border: 1px solid #334155;
          border-radius: 12px;
          padding: 20px;
          max-width: 300px;
        }

        .card-header {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          margin-bottom: 16px;
        }

        .ide-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 48px;
          height: 48px;
          background: linear-gradient(135deg, #007acc 0%, #0098ff 100%);
          border-radius: 10px;
          color: white;
        }

        .card-title h3 {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
          color: #f1f5f9;
        }

        .card-title p {
          margin: 4px 0 0;
          font-size: 13px;
          color: #94a3b8;
        }

        .card-body {
          margin-bottom: 16px;
        }

        .feature-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .feature-list li {
          padding: 6px 0;
          font-size: 13px;
          color: #cbd5e1;
          border-bottom: 1px solid #334155;
        }

        .feature-list li:last-child {
          border-bottom: none;
        }

        .card-footer {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .launch-button {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          width: 100%;
          padding: 12px;
          background: linear-gradient(135deg, #007acc 0%, #0098ff 100%);
          color: white;
          border: none;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .launch-button:hover:not(:disabled) {
          box-shadow: 0 4px 12px rgba(0, 122, 204, 0.4);
        }

        .launch-button:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }

        .spinner {
          display: inline-block;
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-radius: 50%;
          border-top-color: white;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }

        .error {
          margin: 0;
          padding: 8px;
          background: rgba(220, 38, 38, 0.1);
          border-radius: 6px;
          color: #f87171;
          font-size: 12px;
          text-align: center;
        }
      `}</style>
    </div>
  );
}

export default WebIDELauncher;
