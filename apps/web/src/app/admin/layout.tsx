"use client";

import { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function AdminLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  const navItems = [
    { href: "/admin", label: "대시보드", icon: "📊" },
    { href: "/admin/servers", label: "서버 관리", icon: "🖥️" },
    { href: "/admin/auth", label: "인증 관리", icon: "🔐" },
    { href: "/admin/placement", label: "배치 정책", icon: "📍" },
  ];

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      {/* 사이드바 */}
      <aside
        style={{
          width: "240px",
          backgroundColor: "#24292e",
          color: "white",
          padding: "20px",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div style={{ marginBottom: "32px" }}>
          <h1 style={{ margin: 0, fontSize: "20px", fontWeight: 600 }}>
            관리자 대시보드
          </h1>
        </div>

        <nav style={{ flex: 1 }}>
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  padding: "12px 16px",
                  marginBottom: "4px",
                  borderRadius: "6px",
                  backgroundColor: isActive ? "#2f363d" : "transparent",
                  color: isActive ? "white" : "#c9d1d9",
                  textDecoration: "none",
                  fontSize: "14px",
                  fontWeight: isActive ? 500 : 400,
                }}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div style={{ paddingTop: "20px", borderTop: "1px solid #2f363d" }}>
          <Link
            href="/"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              padding: "12px 16px",
              borderRadius: "6px",
              color: "#c9d1d9",
              textDecoration: "none",
              fontSize: "14px",
            }}
          >
            <span>←</span>
            <span>워크스페이스로 돌아가기</span>
          </Link>
        </div>
      </aside>

      {/* 메인 컨텐츠 */}
      <main style={{ flex: 1, overflow: "auto", backgroundColor: "#f6f8fa" }}>
        {children}
      </main>
    </div>
  );
}
