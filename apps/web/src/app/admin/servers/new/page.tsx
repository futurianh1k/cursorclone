"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { registerServer, RegisterServerRequest } from "@/lib/admin-api";

export default function NewServerPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<RegisterServerRequest>({
    name: "",
    host: "",
    port: 22,
    type: "kubernetes",
    region: "",
    zone: "",
    maxWorkspaces: 100,
    auth: {
      type: "ssh_key",
      private_key: "",
      public_key: "",
    },
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await registerServer(formData);
      router.push("/admin/servers");
    } catch (err: any) {
      setError(err.message || "서버 등록에 실패했습니다");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "32px", maxWidth: "800px" }}>
      <div style={{ marginBottom: "32px" }}>
        <h1 style={{ margin: 0, fontSize: "24px", fontWeight: 600 }}>
          새 서버 등록
        </h1>
        <p style={{ margin: "8px 0 0 0", color: "#656d76", fontSize: "14px" }}>
          인프라 서버를 등록하고 인증 정보를 설정하세요
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <div
          style={{
            backgroundColor: "white",
            borderRadius: "8px",
            border: "1px solid #d1d5da",
            padding: "24px",
          }}
        >
          {/* 기본 정보 */}
          <div style={{ marginBottom: "24px" }}>
            <h2 style={{ margin: "0 0 16px 0", fontSize: "18px", fontWeight: 600 }}>
              기본 정보
            </h2>

            <div style={{ marginBottom: "16px" }}>
              <label
                style={{
                  display: "block",
                  fontSize: "14px",
                  fontWeight: 500,
                  marginBottom: "8px",
                }}
              >
                서버 이름 *
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="k8s-cluster-1"
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  fontSize: "14px",
                  border: "1px solid #d1d5da",
                  borderRadius: "6px",
                }}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "16px", marginBottom: "16px" }}>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "14px",
                    fontWeight: 500,
                    marginBottom: "8px",
                  }}
                >
                  호스트 *
                </label>
                <input
                  type="text"
                  required
                  value={formData.host}
                  onChange={(e) =>
                    setFormData({ ...formData, host: e.target.value })
                  }
                  placeholder="k8s.example.com"
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    fontSize: "14px",
                    border: "1px solid #d1d5da",
                    borderRadius: "6px",
                  }}
                />
              </div>

              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "14px",
                    fontWeight: 500,
                    marginBottom: "8px",
                  }}
                >
                  포트 *
                </label>
                <input
                  type="number"
                  required
                  value={formData.port}
                  onChange={(e) =>
                    setFormData({ ...formData, port: parseInt(e.target.value) })
                  }
                  min={1}
                  max={65535}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    fontSize: "14px",
                    border: "1px solid #d1d5da",
                    borderRadius: "6px",
                  }}
                />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px" }}>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "14px",
                    fontWeight: 500,
                    marginBottom: "8px",
                  }}
                >
                  타입 *
                </label>
                <select
                  required
                  value={formData.type}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      type: e.target.value as "kubernetes" | "docker" | "ssh",
                    })
                  }
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    fontSize: "14px",
                    border: "1px solid #d1d5da",
                    borderRadius: "6px",
                  }}
                >
                  <option value="kubernetes">Kubernetes</option>
                  <option value="docker">Docker</option>
                  <option value="ssh">SSH</option>
                </select>
              </div>

              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "14px",
                    fontWeight: 500,
                    marginBottom: "8px",
                  }}
                >
                  지역
                </label>
                <input
                  type="text"
                  value={formData.region}
                  onChange={(e) =>
                    setFormData({ ...formData, region: e.target.value })
                  }
                  placeholder="us-west-1"
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    fontSize: "14px",
                    border: "1px solid #d1d5da",
                    borderRadius: "6px",
                  }}
                />
              </div>

              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "14px",
                    fontWeight: 500,
                    marginBottom: "8px",
                  }}
                >
                  존
                </label>
                <input
                  type="text"
                  value={formData.zone}
                  onChange={(e) =>
                    setFormData({ ...formData, zone: e.target.value })
                  }
                  placeholder="us-west-1a"
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    fontSize: "14px",
                    border: "1px solid #d1d5da",
                    borderRadius: "6px",
                  }}
                />
              </div>
            </div>
          </div>

          {/* 인증 정보 */}
          <div style={{ marginBottom: "24px", paddingTop: "24px", borderTop: "1px solid #d1d5da" }}>
            <h2 style={{ margin: "0 0 16px 0", fontSize: "18px", fontWeight: 600 }}>
              인증 정보
            </h2>

            <div style={{ marginBottom: "16px" }}>
              <label
                style={{
                  display: "block",
                  fontSize: "14px",
                  fontWeight: 500,
                  marginBottom: "8px",
                }}
              >
                인증 타입 *
              </label>
              <select
                required
                value={formData.auth.type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    auth: {
                      ...formData.auth,
                      type: e.target.value as "ssh_key" | "mtls" | "api_key",
                    },
                  })
                }
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  fontSize: "14px",
                  border: "1px solid #d1d5da",
                  borderRadius: "6px",
                }}
              >
                <option value="ssh_key">SSH 키</option>
                <option value="mtls">mTLS</option>
                <option value="api_key">API 키</option>
              </select>
            </div>

            {formData.auth.type === "ssh_key" && (
              <>
                <div style={{ marginBottom: "16px" }}>
                  <label
                    style={{
                      display: "block",
                      fontSize: "14px",
                      fontWeight: 500,
                      marginBottom: "8px",
                    }}
                  >
                    SSH 비공개키 *
                  </label>
                  <textarea
                    required
                    value={formData.auth.private_key}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        auth: { ...formData.auth, private_key: e.target.value },
                      })
                    }
                    placeholder="-----BEGIN OPENSSH PRIVATE KEY-----..."
                    rows={6}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      fontSize: "14px",
                      fontFamily: "monospace",
                      border: "1px solid #d1d5da",
                      borderRadius: "6px",
                    }}
                  />
                </div>

                <div style={{ marginBottom: "16px" }}>
                  <label
                    style={{
                      display: "block",
                      fontSize: "14px",
                      fontWeight: 500,
                      marginBottom: "8px",
                    }}
                  >
                    SSH 공개키 *
                  </label>
                  <textarea
                    required
                    value={formData.auth.public_key}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        auth: { ...formData.auth, public_key: e.target.value },
                      })
                    }
                    placeholder="ssh-rsa AAAAB3NzaC1yc2E..."
                    rows={3}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      fontSize: "14px",
                      fontFamily: "monospace",
                      border: "1px solid #d1d5da",
                      borderRadius: "6px",
                    }}
                  />
                </div>
              </>
            )}

            {formData.auth.type === "api_key" && (
              <div style={{ marginBottom: "16px" }}>
                <label
                  style={{
                    display: "block",
                    fontSize: "14px",
                    fontWeight: 500,
                    marginBottom: "8px",
                  }}
                >
                  API 키 *
                </label>
                <input
                  type="password"
                  required
                  value={formData.auth.api_key || ""}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      auth: { ...formData.auth, api_key: e.target.value },
                    })
                  }
                  placeholder="API 키를 입력하세요"
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    fontSize: "14px",
                    border: "1px solid #d1d5da",
                    borderRadius: "6px",
                  }}
                />
              </div>
            )}

            {formData.auth.type === "mtls" && (
              <>
                <div style={{ marginBottom: "16px" }}>
                  <label
                    style={{
                      display: "block",
                      fontSize: "14px",
                      fontWeight: 500,
                      marginBottom: "8px",
                    }}
                  >
                    인증서 *
                  </label>
                  <textarea
                    required
                    value={formData.auth.certificate || ""}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        auth: { ...formData.auth, certificate: e.target.value },
                      })
                    }
                    placeholder="-----BEGIN CERTIFICATE-----..."
                    rows={6}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      fontSize: "14px",
                      fontFamily: "monospace",
                      border: "1px solid #d1d5da",
                      borderRadius: "6px",
                    }}
                  />
                </div>

                <div style={{ marginBottom: "16px" }}>
                  <label
                    style={{
                      display: "block",
                      fontSize: "14px",
                      fontWeight: 500,
                      marginBottom: "8px",
                    }}
                  >
                    비공개키 *
                  </label>
                  <textarea
                    required
                    value={formData.auth.private_key || ""}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        auth: { ...formData.auth, private_key: e.target.value },
                      })
                    }
                    placeholder="-----BEGIN PRIVATE KEY-----..."
                    rows={6}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      fontSize: "14px",
                      fontFamily: "monospace",
                      border: "1px solid #d1d5da",
                      borderRadius: "6px",
                    }}
                  />
                </div>
              </>
            )}
          </div>

          {error && (
            <div
              style={{
                padding: "12px",
                marginBottom: "16px",
                backgroundColor: "#ffeef0",
                border: "1px solid #f85149",
                borderRadius: "6px",
                color: "#cf222e",
                fontSize: "14px",
              }}
            >
              {error}
            </div>
          )}

          <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
            <button
              type="button"
              onClick={() => router.back()}
              disabled={loading}
              style={{
                padding: "8px 16px",
                fontSize: "14px",
                backgroundColor: "#f6f8fa",
                color: "#24292e",
                border: "1px solid #d1d5da",
                borderRadius: "6px",
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? 0.6 : 1,
              }}
            >
              취소
            </button>
            <button
              type="submit"
              disabled={loading}
              style={{
                padding: "8px 16px",
                fontSize: "14px",
                fontWeight: 500,
                backgroundColor: "#24292e",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? 0.6 : 1,
              }}
            >
              {loading ? "등록 중..." : "서버 등록"}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
