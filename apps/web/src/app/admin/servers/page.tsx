"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { listServers, testServerConnection } from "@/lib/admin-api";

export default function ServersPage() {
  const [servers, setServers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState<string | null>(null);

  useEffect(() => {
    loadServers();
  }, []);

  const loadServers = async () => {
    try {
      setLoading(true);
      const serverList = await listServers();
      setServers(serverList);
    } catch (err) {
      console.error("Failed to load servers:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async (serverId: string) => {
    setTesting(serverId);
    try {
      const result = await testServerConnection(serverId);
      alert(result.success ? "연결 성공!" : `연결 실패: ${result.message}`);
    } catch (err: any) {
      alert(`연결 테스트 실패: ${err.message}`);
    } finally {
      setTesting(null);
    }
  };

  return (
    <div style={{ padding: "32px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "32px",
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: "24px", fontWeight: 600 }}>
            서버 관리
          </h1>
          <p style={{ margin: "8px 0 0 0", color: "#656d76", fontSize: "14px" }}>
            인프라 서버를 등록하고 관리하세요
          </p>
        </div>
        <Link
          href="/admin/servers/new"
          style={{
            padding: "8px 16px",
            backgroundColor: "#24292e",
            color: "white",
            borderRadius: "6px",
            textDecoration: "none",
            fontSize: "14px",
            fontWeight: 500,
          }}
        >
          + 서버 추가
        </Link>
      </div>

      {loading ? (
        <div style={{ padding: "40px", textAlign: "center", color: "#656d76" }}>
          로딩 중...
        </div>
      ) : servers.length === 0 ? (
        <div
          style={{
            backgroundColor: "white",
            borderRadius: "8px",
            border: "1px solid #d1d5da",
            padding: "40px",
            textAlign: "center",
            color: "#656d76",
          }}
        >
          등록된 서버가 없습니다.
          <br />
          <Link
            href="/admin/servers/new"
            style={{ color: "#0366d6", textDecoration: "none" }}
          >
            첫 번째 서버를 등록하세요
          </Link>
        </div>
      ) : (
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
                  호스트:포트
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
                  타입
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
                  상태
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
                  워크스페이스
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
              {servers.map((server) => (
                <tr
                  key={server.serverId}
                  style={{ borderBottom: "1px solid #f1f3f5" }}
                >
                  <td style={{ padding: "12px 20px", fontSize: "14px" }}>
                    <Link
                      href={`/admin/servers/${server.serverId}`}
                      style={{
                        color: "#0366d6",
                        textDecoration: "none",
                        fontWeight: 500,
                      }}
                    >
                      {server.name}
                    </Link>
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: "14px", color: "#656d76" }}>
                    {server.host}:{server.port}
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: "14px", color: "#656d76" }}>
                    {server.type}
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: "14px" }}>
                    <span
                      style={{
                        padding: "4px 8px",
                        borderRadius: "12px",
                        fontSize: "12px",
                        fontWeight: 500,
                        backgroundColor:
                          server.status === "active"
                            ? "#d4edda"
                            : server.status === "maintenance"
                            ? "#fff3cd"
                            : "#f8d7da",
                        color:
                          server.status === "active"
                            ? "#155724"
                            : server.status === "maintenance"
                            ? "#856404"
                            : "#721c24",
                      }}
                    >
                      {server.status}
                    </span>
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: "14px", color: "#656d76" }}>
                    {server.currentWorkspaces} / {server.maxWorkspaces}
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: "14px" }}>
                    <button
                      onClick={() => handleTestConnection(server.serverId)}
                      disabled={testing === server.serverId}
                      style={{
                        padding: "4px 8px",
                        fontSize: "12px",
                        backgroundColor: "#0366d6",
                        color: "white",
                        border: "none",
                        borderRadius: "4px",
                        cursor: testing === server.serverId ? "not-allowed" : "pointer",
                        opacity: testing === server.serverId ? 0.6 : 1,
                      }}
                    >
                      {testing === server.serverId ? "테스트 중..." : "연결 테스트"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
