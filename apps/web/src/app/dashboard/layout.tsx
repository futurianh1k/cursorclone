"use client";

import { ReactNode, useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { getCurrentUser, logout, User } from "@/lib/auth-api";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUser();
  }, []);

  const loadUser = async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    try {
      const userData = await getCurrentUser(token);
      setUser(userData);
    } catch (err) {
      localStorage.removeItem("access_token");
      router.push("/login");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    const token = localStorage.getItem("access_token");
    if (token) {
      await logout(token);
    }
    localStorage.removeItem("access_token");
    router.push("/login");
  };

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
        }}
      >
        로딩 중...
      </div>
    );
  }

  const navItems = [
    { href: "/dashboard", label: "Overview", icon: "📊" },
    { href: "/dashboard/settings", label: "Settings", icon: "⚙️" },
    { href: "/dashboard/members", label: "Members", icon: "👥" },
    { href: "/dashboard/integrations", label: "Integrations", icon: "🔌" },
    { href: "/dashboard/cloud-agents", label: "Cloud Agents", icon: "☁️" },
    { href: "/dashboard/bugbot", label: "Bugbot", icon: "🐛" },
    { href: "/dashboard/analytics", label: "Analytics", icon: "📈" },
    { href: "/dashboard/usage", label: "Usage", icon: "💳" },
    { href: "/dashboard/docs", label: "Docs", icon: "📚" },
    { href: "/dashboard/contact", label: "Contact Us", icon: "📧" },
  ];

  return (
    <div style={{ display: "flex", height: "100vh", backgroundColor: "#f6f8fa" }}>
      {/* 사이드바 */}
      <aside
        style={{
          width: "260px",
          backgroundColor: "#24292e",
          color: "white",
          display: "flex",
          flexDirection: "column",
          borderRight: "1px solid #2f363d",
        }}
      >
        {/* 로고/브랜드 */}
        <div style={{ padding: "20px", borderBottom: "1px solid #2f363d" }}>
          <Link
            href="/dashboard"
            style={{
              color: "white",
              textDecoration: "none",
              fontSize: "20px",
              fontWeight: 600,
            }}
          >
            Cursor On-Prem
          </Link>
        </div>

        {/* 네비게이션 */}
        <nav style={{ flex: 1, padding: "12px", overflowY: "auto" }}>
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
                  padding: "10px 16px",
                  marginBottom: "4px",
                  borderRadius: "6px",
                  backgroundColor: isActive ? "#2f363d" : "transparent",
                  color: isActive ? "white" : "#c9d1d9",
                  textDecoration: "none",
                  fontSize: "14px",
                  fontWeight: isActive ? 500 : 400,
                  transition: "all 0.2s",
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = "#2f363d";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = "transparent";
                  }
                }}
              >
                <span style={{ fontSize: "18px" }}>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* 사용자 정보 및 로그아웃 */}
        <div style={{ padding: "16px", borderTop: "1px solid #2f363d" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              marginBottom: "12px",
            }}
          >
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                backgroundColor: "#0366d6",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
                fontWeight: 600,
                fontSize: "14px",
              }}
            >
              {user?.name.charAt(0).toUpperCase() || "U"}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: "14px",
                  fontWeight: 500,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {user?.name || "User"}
              </div>
              <div
                style={{
                  fontSize: "12px",
                  color: "#8b949e",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {user?.email || ""}
              </div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            data-testid="dashboard-logout"
            style={{
              width: "100%",
              padding: "8px",
              backgroundColor: "transparent",
              color: "#c9d1d9",
              border: "1px solid #2f363d",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "14px",
            }}
          >
            로그아웃
          </button>
        </div>
      </aside>

      {/* 메인 컨텐츠 */}
      <main style={{ flex: 1, overflow: "auto" }}>{children}</main>
    </div>
  );
}
