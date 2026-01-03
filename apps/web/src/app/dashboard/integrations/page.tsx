"use client";

export default function IntegrationsPage() {
  const integrations = [
    {
      name: "GitHub",
      description: "GitHub 저장소와 연동",
      icon: "🐙",
      connected: false,
    },
    {
      name: "GitLab",
      description: "GitLab 저장소와 연동",
      icon: "🦊",
      connected: false,
    },
    {
      name: "Bitbucket",
      description: "Bitbucket 저장소와 연동",
      icon: "🔵",
      connected: false,
    },
  ];

  return (
    <div style={{ padding: "32px", maxWidth: "1000px", margin: "0 auto" }}>
      <div style={{ marginBottom: "32px" }}>
        <h1 style={{ margin: 0, fontSize: "28px", fontWeight: 600 }}>
          Integrations
        </h1>
        <p style={{ margin: "8px 0 0 0", color: "#656d76", fontSize: "16px" }}>
          외부 서비스와 연동하여 기능을 확장하세요
        </p>
      </div>

      <div style={{ display: "grid", gap: "16px" }}>
        {integrations.map((integration) => (
          <div
            key={integration.name}
            style={{
              backgroundColor: "white",
              borderRadius: "8px",
              border: "1px solid #d1d5da",
              padding: "24px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
              <div style={{ fontSize: "32px" }}>{integration.icon}</div>
              <div>
                <div style={{ fontSize: "18px", fontWeight: 600, marginBottom: "4px" }}>
                  {integration.name}
                </div>
                <div style={{ fontSize: "14px", color: "#656d76" }}>
                  {integration.description}
                </div>
              </div>
            </div>
            <button
              style={{
                padding: "8px 16px",
                fontSize: "14px",
                fontWeight: 500,
                backgroundColor: integration.connected ? "#f6f8fa" : "#24292e",
                color: integration.connected ? "#24292e" : "white",
                border: integration.connected ? "1px solid #d1d5da" : "none",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              {integration.connected ? "연결됨" : "연결"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
