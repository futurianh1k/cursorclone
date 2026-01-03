import { ErrorBoundary } from "@/components/ErrorBoundary";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Cursor On-Prem - AI 코딩 환경",
  description: "금융권 온프레미스 AI 코딩 환경",
};

/**
 * 접근성을 위한 스크린 리더 전용 텍스트 스타일
 */
const srOnlyStyle = `
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
  
  /* 포커스 상태 표시 */
  :focus-visible {
    outline: 2px solid #007acc;
    outline-offset: 2px;
  }
  
  /* 포커스 링 제거 (마우스) */
  :focus:not(:focus-visible) {
    outline: none;
  }
  
  /* 스킵 네비게이션 링크 */
  .skip-link {
    position: absolute;
    top: -40px;
    left: 0;
    background: #007acc;
    color: white;
    padding: 8px 16px;
    z-index: 100;
    text-decoration: none;
    font-weight: 500;
  }
  
  .skip-link:focus {
    top: 0;
  }
  
  /* 고대비 모드 지원 */
  @media (prefers-contrast: high) {
    :focus-visible {
      outline: 3px solid currentColor;
    }
  }
  
  /* 애니메이션 감소 모드 지원 */
  @media (prefers-reduced-motion: reduce) {
    * {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }
  }
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <head>
        <style dangerouslySetInnerHTML={{ __html: srOnlyStyle }} />
      </head>
      <body style={{ margin: 0, fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif" }}>
        {/* 스킵 네비게이션 */}
        <a href="#main-content" className="skip-link">
          메인 콘텐츠로 건너뛰기
        </a>
        
        {/* 전역 에러 바운더리 */}
        <ErrorBoundary name="Application">
          <main id="main-content">
            {children}
          </main>
        </ErrorBoundary>
      </body>
    </html>
  );
}
