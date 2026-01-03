"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";

/**
 * 에러 정보 인터페이스
 */
interface ErrorDetails {
  message: string;
  stack?: string;
  componentStack?: string;
  timestamp: Date;
}

/**
 * ErrorBoundary Props
 */
interface ErrorBoundaryProps {
  children: ReactNode;
  /** 폴백 UI 커스터마이즈 */
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  /** 에러 발생 시 콜백 (로깅용) */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** 에러 발생 영역 이름 (디버깅용) */
  name?: string;
}

/**
 * ErrorBoundary State
 */
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Error Boundary 컴포넌트
 * 
 * 하위 컴포넌트에서 발생하는 JavaScript 에러를 잡아서
 * 전체 앱이 다운되는 것을 방지합니다.
 * 
 * 사용 예:
 * ```tsx
 * <ErrorBoundary name="CodeEditor">
 *   <CodeEditor />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });

    // 에러 로깅
    console.error(
      `[ErrorBoundary${this.props.name ? `: ${this.props.name}` : ""}] 에러 발생:`,
      error,
      errorInfo
    );

    // 외부 에러 핸들러 호출
    this.props.onError?.(error, errorInfo);

    // 프로덕션에서는 에러 리포팅 서비스로 전송
    if (typeof window !== "undefined" && process.env.NODE_ENV === "production") {
      this.reportError(error, errorInfo);
    }
  }

  /**
   * 에러 리포팅 (프로덕션용)
   */
  private reportError(error: Error, errorInfo: ErrorInfo): void {
    const errorDetails: ErrorDetails = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack ?? undefined,
      timestamp: new Date(),
    };

    // TODO: 에러 리포팅 서비스로 전송
    // fetch('/api/error-report', { method: 'POST', body: JSON.stringify(errorDetails) });
    console.log("[ErrorBoundary] 에러 리포트:", errorDetails);
  }

  /**
   * 에러 상태 리셋
   */
  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      // 커스텀 폴백 사용
      if (this.props.fallback) {
        if (typeof this.props.fallback === "function") {
          return this.props.fallback(this.state.error, this.handleReset);
        }
        return this.props.fallback;
      }

      // 기본 폴백 UI
      return (
        <div
          role="alert"
          aria-live="assertive"
          style={{
            padding: "24px",
            backgroundColor: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: "8px",
            margin: "16px",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              marginBottom: "16px",
            }}
          >
            <span
              style={{ fontSize: "24px" }}
              role="img"
              aria-label="경고"
            >
              ⚠️
            </span>
            <h2
              style={{
                margin: 0,
                fontSize: "18px",
                fontWeight: 600,
                color: "#b91c1c",
              }}
            >
              오류가 발생했습니다
            </h2>
          </div>

          <p
            style={{
              margin: "0 0 16px 0",
              fontSize: "14px",
              color: "#7f1d1d",
            }}
          >
            {this.props.name
              ? `${this.props.name} 컴포넌트에서 문제가 발생했습니다.`
              : "컴포넌트에서 문제가 발생했습니다."}
          </p>

          {process.env.NODE_ENV !== "production" && (
            <details
              style={{
                marginBottom: "16px",
                padding: "12px",
                backgroundColor: "#fee2e2",
                borderRadius: "4px",
              }}
            >
              <summary
                style={{
                  cursor: "pointer",
                  fontSize: "13px",
                  fontWeight: 500,
                  color: "#991b1b",
                }}
              >
                오류 상세 정보 (개발 모드)
              </summary>
              <pre
                style={{
                  marginTop: "12px",
                  fontSize: "12px",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  color: "#7f1d1d",
                  maxHeight: "200px",
                  overflow: "auto",
                }}
              >
                {this.state.error.message}
                {"\n\n"}
                {this.state.error.stack}
              </pre>
            </details>
          )}

          <div style={{ display: "flex", gap: "12px" }}>
            <button
              onClick={this.handleReset}
              style={{
                padding: "8px 16px",
                fontSize: "14px",
                fontWeight: 500,
                backgroundColor: "#dc2626",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
              }}
              aria-label="컴포넌트 다시 시도"
            >
              다시 시도
            </button>
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: "8px 16px",
                fontSize: "14px",
                backgroundColor: "white",
                color: "#dc2626",
                border: "1px solid #dc2626",
                borderRadius: "6px",
                cursor: "pointer",
              }}
              aria-label="페이지 새로고침"
            >
              페이지 새로고침
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * 함수형 컴포넌트용 에러 바운더리 래퍼
 */
interface WithErrorBoundaryOptions {
  name?: string;
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  options: WithErrorBoundaryOptions = {}
): React.FC<P> {
  const WrappedComponent: React.FC<P> = (props) => (
    <ErrorBoundary
      name={options.name || Component.displayName || Component.name}
      fallback={options.fallback}
      onError={options.onError}
    >
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `WithErrorBoundary(${
    Component.displayName || Component.name || "Component"
  })`;

  return WrappedComponent;
}

export default ErrorBoundary;
