"use client";

import { useState, useEffect } from "react";
import { listServers } from "@/lib/admin-api";

export default function AdminDashboard() {
  const [servers, setServers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

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

  const totalWorkspaces = servers.reduce((sum, s) => sum + (s.currentWorkspaces || 0), 0);
  const totalCapacity = servers.reduce((sum, s) => sum + (s.maxWorkspaces || 0), 0);
  const activeServers = servers.filter((s) => s.status === "active").length;

  return (
    <div style={{ padding: "32px" }}>
      <div style={{ marginBottom: "32px" }}>
        <h1 style={{ margin: 0, fontSize: "24px", fontWeight: 600 }}>
          관리자 대시보드
        </h1>
        <p style={{ margin: "8px 0 0 0", color: "#656d76", fontSize: "14px" }}>
          인프라 서버 및 워크스페이스 모니터링
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
          title="활성 서버"
          value={activeServers}
          total={servers.length}
          color="#28a745"
        />
        <StatCard
          title="워크스페이스"
          value={totalWorkspaces}
          total={totalCapacity}
          color="#0366d6"
        />
        <StatCard
          title="총 CPU 사용률"
          value={
            servers.length > 0
              ? Math.round(
                  (servers.reduce(
                    (sum, s) => sum + (s.cpuUsage || 0) / (s.cpuCapacity || 1),
                    0
                  ) /
                    servers.length) *
                    100
                )
              : 0
          }
          suffix="%"
          color="#f59e0b"
        />
        <StatCard
          title="총 메모리 사용률"
          value={
            servers.length > 0
              ? Math.round(
                  (servers.reduce(
                    (sum, s) =>
                      sum + (s.memoryUsage || 0) / (s.memoryCapacity || 1),
                    0
                  ) /
                    servers.length) *
                    100
                )
              : 0
          }
          suffix="%"
          color="#dc2626"
        />
      </div>

      {/* 서버 목록 */}
      <div
        style={{
          backgroundColor: "white",
          borderRadius: "8px",
          border: "1px solid #d1d5da",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid #d1d5da",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h2 style={{ margin: 0, fontSize: "18px", fontWeight: 600 }}>
            서버 목록
          </h2>
          <a
            href="/admin/servers/new"
            style={{
              padding: "6px 12px",
              backgroundColor: "#24292e",
              color: "white",
              borderRadius: "6px",
              textDecoration: "none",
              fontSize: "14px",
              fontWeight: 500,
            }}
          >
            + 서버 추가
          </a>
        </div>

        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#656d76" }}>
            로딩 중...
          </div>
        ) : servers.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#656d76" }}>
            등록된 서버가 없습니다.
            <br />
            <a
              href="/admin/servers/new"
              style={{ color: "#0366d6", textDecoration: "none" }}
            >
              첫 번째 서버를 등록하세요
            </a>
          </div>
        ) : (
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
            }}
          >
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
                  호스트
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
                  CPU 사용률
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
                  메모리 사용률
                </th>
              </tr>
            </thead>
            <tbody>
              {servers.map((server) => (
                <tr
                  key={server.serverId}
                  style={{
                    borderBottom: "1px solid #f1f3f5",
                  }}
                >
                  <td style={{ padding: "12px 20px", fontSize: "14px" }}>
                    <a
                      href={`/admin/servers/${server.serverId}`}
                      style={{
                        color: "#0366d6",
                        textDecoration: "none",
                        fontWeight: 500,
                      }}
                    >
                      {server.name}
                    </a>
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
                  <td style={{ padding: "12px 20px", fontSize: "14px", color: "#656d76" }}>
                    {server.cpuCapacity
                      ? `${Math.round(
                          ((server.cpuUsage || 0) / server.cpuCapacity) * 100
                        )}%`
                      : "-"}
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: "14px", color: "#656d76" }}>
                    {server.memoryCapacity
                      ? `${Math.round(
                          ((server.memoryUsage || 0) / server.memoryCapacity) * 100
                        )}%`
                      : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  total,
  suffix = "",
  color,
}: {
  title: string;
  value: number;
  total?: number;
  suffix?: string;
  color: string;
}) {
  return (
    <div
      style={{
        backgroundColor: "white",
        padding: "20px",
        borderRadius: "8px",
        border: "1px solid #d1d5da",
      }}
    >
      <div style={{ fontSize: "14px", color: "#656d76", marginBottom: "8px" }}>
        {title}
      </div>
      <div
        style={{
          fontSize: "32px",
          fontWeight: 600,
          color: color,
          marginBottom: "4px",
        }}
      >
        {value.toLocaleString()}
        {suffix}
        {total !== undefined && (
          <span style={{ fontSize: "16px", color: "#656d76", fontWeight: 400 }}>
            {" "}
            / {total.toLocaleString()}
          </span>
        )}
      </div>
      {total !== undefined && (
        <div style={{ fontSize: "12px", color: "#656d76" }}>
          {Math.round((value / total) * 100)}% 사용 중
        </div>
      )}
    </div>
  );
}
