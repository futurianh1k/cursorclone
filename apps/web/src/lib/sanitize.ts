/**
 * XSS 방어 유틸리티
 * 
 * DOMPurify를 사용한 입력 sanitization
 * 
 * 참조:
 * - DOMPurify: https://github.com/cure53/DOMPurify
 * - OWASP XSS Prevention: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
 */

import DOMPurify from 'dompurify';
import type { Config } from 'dompurify';

// ============================================================
// 기본 설정
// ============================================================

/**
 * 허용할 HTML 태그 (기본값)
 */
const ALLOWED_TAGS = [
  'a', 'abbr', 'acronym', 'address', 'b', 'bdo', 'big', 'blockquote',
  'br', 'cite', 'code', 'dd', 'del', 'dfn', 'div', 'dl', 'dt', 'em',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'ins', 'kbd',
  'li', 'ol', 'p', 'pre', 'q', 's', 'samp', 'small', 'span', 'strong',
  'sub', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr',
  'tt', 'u', 'ul', 'var',
];

/**
 * 허용할 HTML 속성 (기본값)
 */
const ALLOWED_ATTR = [
  'href', 'src', 'alt', 'title', 'class', 'id', 'style', 'target',
  'rel', 'width', 'height', 'colspan', 'rowspan',
];

// ============================================================
// Sanitization 함수
// ============================================================

/**
 * HTML 문자열 sanitize
 * 
 * @param dirty - 신뢰할 수 없는 HTML 문자열
 * @param options - DOMPurify 옵션
 * @returns sanitize된 HTML 문자열
 * 
 * @example
 * const clean = sanitizeHtml('<script>alert("xss")</script><p>Hello</p>');
 * // 결과: '<p>Hello</p>'
 */
export function sanitizeHtml(
  dirty: string,
  options?: Config
): string {
  if (typeof window === 'undefined') {
    // SSR에서는 기본 이스케이프만 수행
    return escapeHtml(dirty);
  }
  
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
    ...options,
  });
}

/**
 * 평문 텍스트로 sanitize (모든 HTML 제거)
 * 
 * @param dirty - 신뢰할 수 없는 문자열
 * @returns 모든 HTML 태그가 제거된 평문 텍스트
 * 
 * @example
 * const text = sanitizeText('<b>Hello</b> <script>alert("xss")</script>');
 * // 결과: 'Hello '
 */
export function sanitizeText(dirty: string): string {
  if (typeof window === 'undefined') {
    return stripHtml(dirty);
  }
  
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: [],
    ALLOWED_ATTR: [],
  });
}

/**
 * URL sanitize (안전하지 않은 프로토콜 제거)
 * 
 * @param url - 신뢰할 수 없는 URL
 * @returns 안전한 URL 또는 빈 문자열
 * 
 * @example
 * sanitizeUrl('javascript:alert("xss")'); // 결과: ''
 * sanitizeUrl('https://example.com'); // 결과: 'https://example.com'
 */
export function sanitizeUrl(url: string): string {
  if (!url) return '';
  
  const trimmed = url.trim().toLowerCase();
  
  // 허용된 프로토콜
  const allowedProtocols = ['http:', 'https:', 'mailto:', 'tel:'];
  
  // 프로토콜 확인
  if (trimmed.startsWith('javascript:') ||
      trimmed.startsWith('data:') ||
      trimmed.startsWith('vbscript:')) {
    return '';
  }
  
  // 상대 URL 또는 허용된 프로토콜
  try {
    const urlObj = new URL(url, 'https://example.com');
    if (allowedProtocols.includes(urlObj.protocol)) {
      return url;
    }
    return '';
  } catch {
    // 상대 URL인 경우
    if (url.startsWith('/') || url.startsWith('#')) {
      return url;
    }
    return '';
  }
}

/**
 * 마크다운 코드 블록 sanitize
 * 
 * AI 응답에서 코드 블록을 안전하게 표시
 * 
 * @param markdown - 마크다운 문자열
 * @returns sanitize된 마크다운
 */
export function sanitizeMarkdown(markdown: string): string {
  if (typeof window === 'undefined') {
    return escapeHtml(markdown);
  }
  
  // 마크다운에서는 더 많은 태그 허용
  return DOMPurify.sanitize(markdown, {
    ALLOWED_TAGS: [
      ...ALLOWED_TAGS,
      'input', // 체크박스용
    ],
    ALLOWED_ATTR: [
      ...ALLOWED_ATTR,
      'type', 'checked', 'disabled', // 체크박스용
    ],
    FORBID_TAGS: ['script', 'style', 'iframe', 'form', 'object', 'embed'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover'],
  });
}

// ============================================================
// 헬퍼 함수
// ============================================================

/**
 * HTML 특수 문자 이스케이프 (SSR용)
 */
function escapeHtml(unsafe: string): string {
  return unsafe
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * HTML 태그 제거 (SSR용)
 */
function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, '');
}

// ============================================================
// React 훅
// ============================================================

/**
 * 사용자 입력을 안전하게 처리하는 훅
 * 
 * @example
 * const { sanitized, setInput } = useSanitizedInput('');
 * // 입력 시 자동으로 sanitize됨
 */
export function useSanitizedInput(initialValue: string = '') {
  const [raw, setRaw] = React.useState(initialValue);
  const sanitized = React.useMemo(() => sanitizeText(raw), [raw]);
  
  return {
    raw,
    sanitized,
    setInput: setRaw,
  };
}

import React from 'react';

/**
 * 안전한 HTML 렌더링 컴포넌트
 * 
 * @example
 * <SafeHtml html={untrustedHtml} />
 */
export function SafeHtml({
  html,
  className,
  as: Component = 'div',
}: {
  html: string;
  className?: string;
  as?: keyof JSX.IntrinsicElements;
}) {
  const clean = React.useMemo(() => sanitizeHtml(html), [html]);
  
  return React.createElement(Component, {
    className,
    dangerouslySetInnerHTML: { __html: clean },
  });
}
