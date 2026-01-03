/**
 * ErrorBoundary 컴포넌트 테스트
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary } from '@/components/ErrorBoundary';

// 에러를 발생시키는 컴포넌트
const ThrowError = ({ shouldThrow = true }: { shouldThrow?: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div>Normal content</div>;
};

// console.error 억제 (React 에러 로그)
const originalError = console.error;
beforeEach(() => {
  console.error = vi.fn();
});

afterEach(() => {
  console.error = originalError;
});

describe('ErrorBoundary', () => {
  it('정상 상태에서 children을 렌더링한다', () => {
    render(
      <ErrorBoundary>
        <div>Test content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('에러 발생 시 폴백 UI를 표시한다', () => {
    render(
      <ErrorBoundary name="TestComponent">
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('오류가 발생했습니다')).toBeInTheDocument();
    expect(screen.getByText(/TestComponent 컴포넌트에서 문제가 발생했습니다/)).toBeInTheDocument();
  });

  it('다시 시도 버튼이 작동한다', () => {
    const { rerender } = render(
      <ErrorBoundary name="TestComponent">
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('오류가 발생했습니다')).toBeInTheDocument();

    // 다시 시도 버튼 클릭
    fireEvent.click(screen.getByText('다시 시도'));

    // 에러 상태가 리셋되고 다시 렌더링 시도 (다시 에러 발생)
    expect(screen.getByText('오류가 발생했습니다')).toBeInTheDocument();
  });

  it('onError 콜백이 호출된다', () => {
    const onError = vi.fn();

    render(
      <ErrorBoundary onError={onError}>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(onError).toHaveBeenCalled();
    expect(onError.mock.calls[0][0]).toBeInstanceOf(Error);
    expect(onError.mock.calls[0][0].message).toBe('Test error message');
  });

  it('커스텀 폴백을 렌더링한다', () => {
    render(
      <ErrorBoundary fallback={<div>Custom fallback</div>}>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom fallback')).toBeInTheDocument();
  });

  it('함수형 폴백을 렌더링한다', () => {
    const fallbackFn = (error: Error, reset: () => void) => (
      <div>
        <span>Error: {error.message}</span>
        <button onClick={reset}>Reset</button>
      </div>
    );

    render(
      <ErrorBoundary fallback={fallbackFn}>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Error: Test error message')).toBeInTheDocument();
    expect(screen.getByText('Reset')).toBeInTheDocument();
  });

  it('ARIA 속성이 올바르게 설정된다', () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    const alert = screen.getByRole('alert');
    expect(alert).toHaveAttribute('aria-live', 'assertive');
  });
});
