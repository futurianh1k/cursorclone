"use client";

export default function UsagePage() {
  return (
    <div style={{ padding: "32px", maxWidth: "1000px", margin: "0 auto" }}>
      <div style={{ marginBottom: "32px" }}>
        <h1 style={{ margin: 0, fontSize: "28px", fontWeight: 600 }}>
          Usage
        </h1>
        <p style={{ margin: "8px 0 0 0", color: "#656d76", fontSize: "16px" }}>
          사용량 및 할당량 관리
        </p>
      </div>

      <div
        style={{
          backgroundColor: "white",
          borderRadius: "8px",
          border: "1px solid #d1d5da",
          padding: "24px",
        }}
      >
        <h2 style={{ margin: "0 0 20px 0", fontSize: "20px", fontWeight: 600 }}>
          이번 달 사용량
        </h2>

        <div style={{ display: "grid", gap: "16px" }}>
          <UsageItem label="워크스페이스" used={0} limit={100} />
          <UsageItem label="AI 요청" used={0} limit={1000} />
          <UsageItem label="토큰 사용량" used={0} limit={100000} />
        </div>
      </div>
    </div>
  );
}

function UsageItem({ label, used, limit }: { label: string; used: number; limit: number }) {
  const percentage = limit > 0 ? (used / limit) * 100 : 0;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
        <span style={{ fontSize: "14px", fontWeight: 500 }}>{label}</span>
        <span style={{ fontSize: "14px", color: "#656d76" }}>
          {used.toLocaleString()} / {limit.toLocaleString()}
        </span>
      </div>
      <div
        style={{
          width: "100%",
          height: "8px",
          backgroundColor: "#f1f3f5",
          borderRadius: "4px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${Math.min(percentage, 100)}%`,
            height: "100%",
            backgroundColor: percentage > 80 ? "#cf222e" : percentage > 50 ? "#f59e0b" : "#28a745",
            transition: "width 0.3s",
          }}
        />
      </div>
    </div>
  );
}
