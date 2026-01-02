"use client";

import { useState, useEffect } from "react";
import { getCurrentUser, User } from "@/lib/auth-api";

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
  });

  useEffect(() => {
    loadUser();
  }, []);

  const loadUser = async () => {
    try {
      const token = localStorage.getItem("access_token");
      if (token) {
        const userData = await getCurrentUser(token);
        setUser(userData);
        setFormData({
          name: userData.name,
          email: userData.email,
        });
      }
    } catch (err) {
      console.error("Failed to load user:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    // TODO: API 호출
    setTimeout(() => {
      setSaving(false);
      alert("설정이 저장되었습니다");
    }, 1000);
  };

  if (loading) {
    return <div style={{ padding: "40px" }}>로딩 중...</div>;
  }

  return (
    <div style={{ padding: "32px", maxWidth: "800px", margin: "0 auto" }}>
      <h1 style={{ margin: "0 0 32px 0", fontSize: "28px", fontWeight: 600 }}>
        Settings
      </h1>

      {/* 프로필 설정 */}
      <div
        style={{
          backgroundColor: "white",
          borderRadius: "8px",
          border: "1px solid #d1d5da",
          padding: "24px",
          marginBottom: "24px",
        }}
      >
        <h2 style={{ margin: "0 0 20px 0", fontSize: "20px", fontWeight: 600 }}>
          프로필
        </h2>

        <div style={{ marginBottom: "20px" }}>
          <label
            style={{
              display: "block",
              fontSize: "14px",
              fontWeight: 500,
              marginBottom: "8px",
            }}
          >
            이름
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            style={{
              width: "100%",
              padding: "8px 12px",
              fontSize: "14px",
              border: "1px solid #d1d5da",
              borderRadius: "6px",
            }}
          />
        </div>

        <div style={{ marginBottom: "20px" }}>
          <label
            style={{
              display: "block",
              fontSize: "14px",
              fontWeight: 500,
              marginBottom: "8px",
            }}
          >
            이메일
          </label>
          <input
            type="email"
            value={formData.email}
            disabled
            style={{
              width: "100%",
              padding: "8px 12px",
              fontSize: "14px",
              border: "1px solid #d1d5da",
              borderRadius: "6px",
              backgroundColor: "#f6f8fa",
              color: "#656d76",
            }}
          />
          <p style={{ margin: "4px 0 0 0", fontSize: "12px", color: "#656d76" }}>
            이메일은 변경할 수 없습니다
          </p>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            padding: "8px 16px",
            fontSize: "14px",
            fontWeight: 500,
            backgroundColor: "#24292e",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: saving ? "not-allowed" : "pointer",
            opacity: saving ? 0.6 : 1,
          }}
        >
          {saving ? "저장 중..." : "저장"}
        </button>
      </div>

      {/* 환경 설정 */}
      <div
        style={{
          backgroundColor: "white",
          borderRadius: "8px",
          border: "1px solid #d1d5da",
          padding: "24px",
        }}
      >
        <h2 style={{ margin: "0 0 20px 0", fontSize: "20px", fontWeight: 600 }}>
          환경 설정
        </h2>

        <div style={{ marginBottom: "16px" }}>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              cursor: "pointer",
            }}
          >
            <input type="checkbox" defaultChecked style={{ width: "18px", height: "18px" }} />
            <div>
              <div style={{ fontSize: "14px", fontWeight: 500 }}>이메일 알림</div>
              <div style={{ fontSize: "12px", color: "#656d76" }}>
                중요한 업데이트를 이메일로 받습니다
              </div>
            </div>
          </label>
        </div>

        <div style={{ marginBottom: "16px" }}>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              cursor: "pointer",
            }}
          >
            <input type="checkbox" defaultChecked style={{ width: "18px", height: "18px" }} />
            <div>
              <div style={{ fontSize: "14px", fontWeight: 500 }}>다크 모드</div>
              <div style={{ fontSize: "12px", color: "#656d76" }}>
                어두운 테마를 사용합니다
              </div>
            </div>
          </label>
        </div>
      </div>
    </div>
  );
}
