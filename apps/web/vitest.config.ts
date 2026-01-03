/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    // 테스트 환경
    environment: 'jsdom',
    
    // 글로벌 설정 (describe, it, expect 등)
    globals: true,
    
    // 셋업 파일
    setupFiles: ['./src/__tests__/setup.ts'],
    
    // 테스트 파일 패턴
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    
    // 제외 패턴
    exclude: ['node_modules', '.next', 'dist'],
    
    // 커버리지 설정
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.test.{ts,tsx}',
        'src/**/*.spec.{ts,tsx}',
        'src/__tests__/**',
        'src/**/*.d.ts',
      ],
      // 커버리지 목표
      thresholds: {
        statements: 50,
        branches: 50,
        functions: 50,
        lines: 50,
      },
    },
    
    // 타임아웃
    testTimeout: 10000,
    
    // 병렬 실행
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: false,
      },
    },
  },
  
  // 경로 별칭
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
