"use client";

import { useState } from "react";

export default function MembersPage() {
  const [members] = useState([
    { name: "홍길동", email: "hong@example.com", role: "admin", joinedAt: "2025-01-01" },
  ]);

  return (
    <div style={{ padding: "32px", maxWidth: "1000px", margin: "0 auto" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "32px",
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: "28px", fontWeight: 600 }}>
            Members
          </h1>
          <p style={{ margin: "8px 0 0 0", color: "#656d76", fontSize: "16px" }}>
            팀원을 관리하고 권한을 설정하세요
          </p>
        </div>
        <button
          style={{
            padding: "8px 16px",
            fontSize: "14px",
            fontWeight: 500,
            backgroundColor: "#24292e",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
          }}
        >
          + 멤버 초대
        </button>
      </div>

      <div
        style={{
          backgroundColor: "white",
          borderRadius: "8px",
          border: "1px solid #d1d5da",
          overflow: "hidden",
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ backgroundColor: "#f6f8fa" }}>
              <th
                style={{
                  padding: "12px 20px",
                  textAlign: "left",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "#656d76",
                  borderBottom: "1px solid #d1d5da",
                }}
              >
                이름
              </th>
              <th
                style={{
                  padding: "12px 20px",
                  textAlign: "left",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "#656d76",
                  borderBottom: "1px solid #d1d5da",
                }}
              >
                이메일
              </th>
              <th
                style={{
                  padding: "12px 20px",
                  textAlign: "left",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "#656d76",
                  borderBottom: "1px solid #d1d5da",
                }}
              >
                역할
              </th>
              <th
                style={{
                  padding: "12px 20px",
                  textAlign: "left",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "#656d76",
                  borderBottom: "1px solid #d1d5da",
                }}
              >
                가입일
              </th>
              <th
                style={{
                  padding: "12px 20px",
                  textAlign: "left",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "#656d76",
                  borderBottom: "1px solid #d1d5da",
                }}
              >
                작업
              </th>
            </tr>
          </thead>
          <tbody>
            {members.map((member, idx) => (
              <tr key={idx} style={{ borderBottom: "1px solid #f1f3f5" }}>
                <td style={{ padding: "12px 20px", fontSize: "14px" }}>{member.name}</td>
                <td style={{ padding: "12px 20px", fontSize: "14px", color: "#656d76" }}>
                  {member.email}
                </td>
                <td style={{ padding: "12px 20px", fontSize: "14px" }}>
                  <span
                    style={{
                      padding: "4px 8px",
                      borderRadius: "12px",
                      fontSize: "12px",
                      fontWeight: 500,
                      backgroundColor: member.role === "admin" ? "#d4edda" : "#e7f3ff",
                      color: member.role === "admin" ? "#155724" : "#0366d6",
                    }}
                  >
                    {member.role}
                  </span>
                </td>
                <td style={{ padding: "12px 20px", fontSize: "14px", color: "#656d76" }}>
                  {member.joinedAt}
                </td>
                <td style={{ padding: "12px 20px", fontSize: "14px" }}>
                  <button
                    style={{
                      padding: "4px 8px",
                      fontSize: "12px",
                      backgroundColor: "transparent",
                      color: "#cf222e",
                      border: "1px solid #d1d5da",
                      borderRadius: "4px",
                      cursor: "pointer",
                    }}
                  >
                    제거
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
