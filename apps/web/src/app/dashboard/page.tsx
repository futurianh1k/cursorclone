"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { listWorkspaces, deleteWorkspace, getWorkspaceIDEUrl, Workspace } from "@/lib/api";
import { getCurrentUser, User } from "@/lib/auth-api";

export default function DashboardOverview() {
  const [user, setUser] = useState<User | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem("access_token");
      if (token) {
        const userData = await getCurrentUser(token);
        setUser(userData);
      }
      const wsList = await listWorkspaces();
      setWorkspaces(wsList);
    } catch (err) {
      console.error("Failed to load data:", err);
    } finally {
      setLoading(false);
    }
  };

  // 워크스페이스 IDE 시작 (열기)
  const handleStartWorkspace = async (workspaceId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setActionLoading(workspaceId);
    setError(null);
    
    try {
      const result = await getWorkspaceIDEUrl(workspaceId);
      // 새 탭에서 IDE 열기
      window.open(result.url, "_blank");
    } catch (err) {
      const message = err instanceof Error ? err.message : "IDE 시작에 실패했습니다";
      setError(message);
      console.error("Failed to start IDE:", err);
    } finally {
      setActionLoading(null);
    }
  };

  // 워크스페이스 삭제
  const handleDeleteWorkspace = async (workspaceId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (deleteConfirm !== workspaceId) {
      setDeleteConfirm(workspaceId);
      return;
    }
    
    setActionLoading(workspaceId);
    setError(null);
    
    try {
      await deleteWorkspace(workspaceId);
      setWorkspaces(workspaces.filter(ws => ws.workspaceId !== workspaceId));
      setDeleteConfirm(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "삭제에 실패했습니다";
      setError(message);
      console.error("Failed to delete workspace:", err);
    } finally {
      setActionLoading(null);
    }
  };

  // 삭제 확인 취소
  const handleCancelDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDeleteConfirm(null);
  };

  if (loading) {
    return (
      <div style={{ padding: "40px", textAlign: "center" }}>
        로딩 중...
      </div>
    );
  }

  return (
    <div style={{ padding: "32px", maxWidth: "1200px", margin: "0 auto" }}>
      {/* 헤더 */}
      <div style={{ marginBottom: "32px" }}>
        <h1 style={{ margin: 0, fontSize: "28px", fontWeight: 600 }}>
          Overview
        </h1>
        <p style={{ margin: "8px 0 0 0", color: "#656d76", fontSize: "16px" }}>
          환영합니다, {user?.name}님!
        </p>
      </div>

      {/* 통계 카드 */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "16px",
          marginBottom: "32px",
        }}
      >
        <StatCard
          title="워크스페이스"
          value={workspaces.length}
          icon="📁"
          color="#0366d6"
          href="/"
        />
        <StatCard
          title="활성 세션"
          value={0}
          icon="🟢"
          color="#28a745"
        />
        <StatCard
          title="이번 달 사용량"
          value="0"
          suffix=" tokens"
          icon="💳"
          color="#f59e0b"
        />
        <StatCard
          title="팀원"
          value={1}
          icon="👥"
          color="#8b5cf6"
          href="/dashboard/members"
        />
      </div>

      {/* 최근 워크스페이스 */}
      <div
        style={{
          backgroundColor: "white",
          borderRadius: "8px",
          border: "1px solid #d1d5da",
          padding: "24px",
          marginBottom: "24px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "20px",
          }}
        >
          <h2 style={{ margin: 0, fontSize: "20px", fontWeight: 600 }}>
            최근 워크스페이스
          </h2>
          <Link
            href="/"
            style={{
              color: "#0366d6",
              textDecoration: "none",
              fontSize: "14px",
            }}
          >
            모두 보기 →
          </Link>
        </div>

        {error && (
          <div
            style={{
              padding: "12px 16px",
              marginBottom: "16px",
              backgroundColor: "#ffeef0",
              border: "1px solid #f85149",
              borderRadius: "6px",
              color: "#cf222e",
              fontSize: "14px",
            }}
          >
            {error}
            <button
              onClick={() => setError(null)}
              style={{
                marginLeft: "12px",
                background: "none",
                border: "none",
                color: "#cf222e",
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              ✕
            </button>
          </div>
        )}

        {workspaces.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#656d76" }}>
            워크스페이스가 없습니다.
            <br />
            <Link
              href="/"
              style={{
                color: "#0366d6",
                textDecoration: "none",
                marginTop: "8px",
                display: "inline-block",
              }}
            >
              새 워크스페이스를 만들어보세요
            </Link>
          </div>
        ) : (
          <div style={{ display: "grid", gap: "12px" }}>
            {workspaces.slice(0, 5).map((ws) => (
              <div
                key={ws.workspaceId}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "16px",
                  padding: "16px",
                  borderRadius: "6px",
                  border: "1px solid #f1f3f5",
                  transition: "all 0.2s",
                  backgroundColor: deleteConfirm === ws.workspaceId ? "#fff5f5" : "transparent",
                }}
                onMouseEnter={(e) => {
                  if (deleteConfirm !== ws.workspaceId) {
                    e.currentTarget.style.backgroundColor = "#f6f8fa";
                    e.currentTarget.style.borderColor = "#d1d5da";
                  }
                }}
                onMouseLeave={(e) => {
                  if (deleteConfirm !== ws.workspaceId) {
                    e.currentTarget.style.backgroundColor = "transparent";
                    e.currentTarget.style.borderColor = "#f1f3f5";
                  }
                }}
              >
                <div
                  style={{
                    width: "40px",
                    height: "40px",
                    borderRadius: "6px",
                    backgroundColor: "#0366d6",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "white",
                    fontSize: "20px",
                  }}
                >
                  📁
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: "16px", fontWeight: 500, marginBottom: "4px" }}>
                    {ws.name}
                  </div>
                  <div style={{ fontSize: "14px", color: "#656d76" }}>
                    {ws.rootPath}
                  </div>
                </div>

                {/* 액션 버튼들 */}
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  {deleteConfirm === ws.workspaceId ? (
                    <>
                      <span style={{ fontSize: "13px", color: "#cf222e", marginRight: "8px" }}>
                        삭제하시겠습니까?
                      </span>
                      <button
                        onClick={(e) => handleDeleteWorkspace(ws.workspaceId, e)}
                        disabled={actionLoading === ws.workspaceId}
                        style={{
                          padding: "6px 12px",
                          fontSize: "13px",
                          fontWeight: 500,
                          backgroundColor: "#cf222e",
                          color: "white",
                          border: "none",
                          borderRadius: "6px",
                          cursor: actionLoading === ws.workspaceId ? "not-allowed" : "pointer",
                          opacity: actionLoading === ws.workspaceId ? 0.6 : 1,
                        }}
                      >
                        {actionLoading === ws.workspaceId ? "삭제 중..." : "확인"}
                      </button>
                      <button
                        onClick={handleCancelDelete}
                        disabled={actionLoading === ws.workspaceId}
                        style={{
                          padding: "6px 12px",
                          fontSize: "13px",
                          fontWeight: 500,
                          backgroundColor: "#f6f8fa",
                          color: "#24292e",
                          border: "1px solid #d1d5da",
                          borderRadius: "6px",
                          cursor: "pointer",
                        }}
                      >
                        취소
                      </button>
                    </>
                  ) : (
                    <>
                      {/* IDE 시작 버튼 */}
                      <button
                        onClick={(e) => handleStartWorkspace(ws.workspaceId, e)}
                        disabled={actionLoading === ws.workspaceId}
                        title="VS Code에서 열기"
                        style={{
                          padding: "6px 12px",
                          fontSize: "13px",
                          fontWeight: 500,
                          backgroundColor: "#238636",
                          color: "white",
                          border: "none",
                          borderRadius: "6px",
                          cursor: actionLoading === ws.workspaceId ? "not-allowed" : "pointer",
                          opacity: actionLoading === ws.workspaceId ? 0.6 : 1,
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                        }}
                      >
                        {actionLoading === ws.workspaceId ? (
                          "시작 중..."
                        ) : (
                          <>
                            <span>▶</span> 시작
                          </>
                        )}
                      </button>

                      {/* 삭제 버튼 */}
                      <button
                        onClick={(e) => handleDeleteWorkspace(ws.workspaceId, e)}
                        disabled={actionLoading === ws.workspaceId}
                        title="워크스페이스 삭제"
                        style={{
                          padding: "6px 12px",
                          fontSize: "13px",
                          fontWeight: 500,
                          backgroundColor: "transparent",
                          color: "#656d76",
                          border: "1px solid #d1d5da",
                          borderRadius: "6px",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = "#cf222e";
                          e.currentTarget.style.color = "#cf222e";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = "#d1d5da";
                          e.currentTarget.style.color = "#656d76";
                        }}
                      >
                        🗑️ 삭제
                      </button>

                      {/* 상세 보기 링크 */}
                      <Link
                        href={`/?workspace=${ws.workspaceId}`}
                        style={{
                          padding: "6px 12px",
                          fontSize: "13px",
                          color: "#0366d6",
                          textDecoration: "none",
                        }}
                      >
                        →
                      </Link>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 빠른 작업 */}
      <div
        style={{
          backgroundColor: "white",
          borderRadius: "8px",
          border: "1px solid #d1d5da",
          padding: "24px",
        }}
      >
        <h2 style={{ margin: "0 0 20px 0", fontSize: "20px", fontWeight: 600 }}>
          빠른 작업
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px" }}>
          <QuickAction
            icon="➕"
            title="새 워크스페이스"
            description="빈 워크스페이스 생성"
            href="/"
          />
          <QuickAction
            icon="🔗"
            title="GitHub 클론"
            description="저장소 클론"
            href="/"
          />
          <QuickAction
            icon="⚙️"
            title="설정"
            description="환경 설정"
            href="/dashboard/settings"
          />
          <QuickAction
            icon="📚"
            title="문서"
            description="사용 가이드"
            href="/dashboard/docs"
          />
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  suffix = "",
  icon,
  color,
  href,
}: {
  title: string;
  value: number | string;
  suffix?: string;
  icon: string;
  color: string;
  href?: string;
}) {
  const content = (
    <div
      style={{
        backgroundColor: "white",
        padding: "20px",
        borderRadius: "8px",
        border: "1px solid #d1d5da",
        cursor: href ? "pointer" : "default",
        transition: "all 0.2s",
      }}
      onMouseEnter={(e) => {
        if (href) {
          e.currentTarget.style.borderColor = color;
          e.currentTarget.style.boxShadow = `0 2px 8px ${color}20`;
        }
      }}
      onMouseLeave={(e) => {
        if (href) {
          e.currentTarget.style.borderColor = "#d1d5da";
          e.currentTarget.style.boxShadow = "none";
        }
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
        <div style={{ fontSize: "24px" }}>{icon}</div>
        <div
          style={{
            fontSize: "32px",
            fontWeight: 600,
            color: color,
          }}
        >
          {typeof value === "number" ? value.toLocaleString() : value}
          {suffix}
        </div>
      </div>
      <div style={{ fontSize: "14px", color: "#656d76" }}>{title}</div>
    </div>
  );

  if (href) {
    return (
      <Link href={href} style={{ textDecoration: "none", color: "inherit" }}>
        {content}
      </Link>
    );
  }

  return content;
}

function QuickAction({
  icon,
  title,
  description,
  href,
}: {
  icon: string;
  title: string;
  description: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      style={{
        display: "block",
        padding: "16px",
        borderRadius: "6px",
        border: "1px solid #f1f3f5",
        textDecoration: "none",
        color: "inherit",
        transition: "all 0.2s",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = "#f6f8fa";
        e.currentTarget.style.borderColor = "#d1d5da";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = "transparent";
        e.currentTarget.style.borderColor = "#f1f3f5";
      }}
    >
      <div style={{ fontSize: "24px", marginBottom: "8px" }}>{icon}</div>
      <div style={{ fontSize: "16px", fontWeight: 500, marginBottom: "4px" }}>
        {title}
      </div>
      <div style={{ fontSize: "14px", color: "#656d76" }}>{description}</div>
    </Link>
  );
}
