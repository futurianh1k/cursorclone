"use client";

export default function BugbotPage() {
  return (
    <div style={{ padding: "32px", maxWidth: "1000px", margin: "0 auto" }}>
      <div style={{ marginBottom: "32px" }}>
        <h1 style={{ margin: 0, fontSize: "28px", fontWeight: 600 }}>
          Bugbot
        </h1>
        <p style={{ margin: "8px 0 0 0", color: "#656d76", fontSize: "16px" }}>
          AI 기반 버그 탐지 및 수정 도우미
        </p>
      </div>

      <div
        style={{
          backgroundColor: "white",
          borderRadius: "8px",
          border: "1px solid #d1d5da",
          padding: "40px",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: "48px", marginBottom: "16px" }}>🐛</div>
        <h2 style={{ margin: "0 0 8px 0", fontSize: "20px", fontWeight: 600 }}>
          Bugbot
        </h2>
        <p style={{ margin: 0, color: "#656d76", fontSize: "14px" }}>
          버그 탐지 기능은 곧 출시될 예정입니다
        </p>
      </div>
    </div>
  );
}
