"use client";

import { useState } from "react";

export default function ContactPage() {
  const [formData, setFormData] = useState({
    subject: "",
    message: "",
  });
  const [sending, setSending] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSending(true);
    // TODO: API 호출
    setTimeout(() => {
      setSending(false);
      alert("문의가 전송되었습니다");
      setFormData({ subject: "", message: "" });
    }, 1000);
  };

  return (
    <div style={{ padding: "32px", maxWidth: "800px", margin: "0 auto" }}>
      <div style={{ marginBottom: "32px" }}>
        <h1 style={{ margin: 0, fontSize: "28px", fontWeight: 600 }}>
          Contact Us
        </h1>
        <p style={{ margin: "8px 0 0 0", color: "#656d76", fontSize: "16px" }}>
          문의사항이나 피드백을 보내주세요
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
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "20px" }}>
            <label
              style={{
                display: "block",
                fontSize: "14px",
                fontWeight: 500,
                marginBottom: "8px",
              }}
            >
              제목 *
            </label>
            <input
              type="text"
              required
              value={formData.subject}
              onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
              placeholder="문의 제목"
              style={{
                width: "100%",
                padding: "8px 12px",
                fontSize: "14px",
                border: "1px solid #d1d5da",
                borderRadius: "6px",
              }}
            />
          </div>

          <div style={{ marginBottom: "24px" }}>
            <label
              style={{
                display: "block",
                fontSize: "14px",
                fontWeight: 500,
                marginBottom: "8px",
              }}
            >
              메시지 *
            </label>
            <textarea
              required
              value={formData.message}
              onChange={(e) => setFormData({ ...formData, message: e.target.value })}
              placeholder="문의 내용을 입력하세요"
              rows={8}
              style={{
                width: "100%",
                padding: "8px 12px",
                fontSize: "14px",
                border: "1px solid #d1d5da",
                borderRadius: "6px",
                fontFamily: "inherit",
              }}
            />
          </div>

          <button
            type="submit"
            disabled={sending}
            style={{
              padding: "8px 16px",
              fontSize: "14px",
              fontWeight: 500,
              backgroundColor: "#24292e",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: sending ? "not-allowed" : "pointer",
              opacity: sending ? 0.6 : 1,
            }}
          >
            {sending ? "전송 중..." : "전송"}
          </button>
        </form>
      </div>
    </div>
  );
}
