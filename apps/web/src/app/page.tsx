"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * 메인 페이지 - 대시보드로 리다이렉트
 * 기존 워크스페이스 선택/편집 UI는 제거됨
 * 모든 워크스페이스 관리는 대시보드에서 처리
 */
export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // 인증 확인 후 대시보드로 리다이렉트
    const token = localStorage.getItem("access_token");
    if (token) {
      router.replace("/dashboard");
    } else {
      router.replace("/login");
    }
  }, [router]);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        fontSize: "14px",
        color: "#666",
      }}
    >
      로딩 중...
    </div>
  );
}
