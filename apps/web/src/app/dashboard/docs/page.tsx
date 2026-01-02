"use client";

export default function DocsPage() {
  const docs = [
    { title: "시작하기", description: "Cursor On-Prem 사용 가이드", href: "#" },
    { title: "워크스페이스 관리", description: "워크스페이스 생성 및 관리", href: "#" },
    { title: "AI 기능 사용", description: "코드 설명 및 리라이트", href: "#" },
    { title: "API 문서", description: "REST API 참조", href: "#" },
  ];

  return (
    <div style={{ padding: "32px", maxWidth: "1000px", margin: "0 auto" }}>
      <div style={{ marginBottom: "32px" }}>
        <h1 style={{ margin: 0, fontSize: "28px", fontWeight: 600 }}>
          Docs
        </h1>
        <p style={{ margin: "8px 0 0 0", color: "#656d76", fontSize: "16px" }}>
          사용 가이드 및 문서
        </p>
      </div>

      <div style={{ display: "grid", gap: "16px" }}>
        {docs.map((doc) => (
          <a
            key={doc.title}
            href={doc.href}
            style={{
              display: "block",
              backgroundColor: "white",
              borderRadius: "8px",
              border: "1px solid #d1d5da",
              padding: "20px",
              textDecoration: "none",
              color: "inherit",
              transition: "all 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "#0366d6";
              e.currentTarget.style.boxShadow = "0 2px 8px rgba(3, 102, 214, 0.1)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "#d1d5da";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            <div style={{ fontSize: "18px", fontWeight: 600, marginBottom: "8px" }}>
              {doc.title}
            </div>
            <div style={{ fontSize: "14px", color: "#656d76" }}>{doc.description}</div>
          </a>
        ))}
      </div>
    </div>
  );
}
