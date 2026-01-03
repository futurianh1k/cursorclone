/** @type {import('next').NextConfig} */

// 번들 분석기 (ANALYZE=true pnpm build)
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
});

const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  
  // Docker 환경에서 정적 파일 서빙을 위한 설정
  images: {
    unoptimized: true,
  },
  
  // ============================================================
  // 번들 사이즈 최적화
  // ============================================================
  
  // 프로덕션에서 소스맵 비활성화 (번들 사이즈 감소)
  productionBrowserSourceMaps: false,
  
  // SWC 미니파이 활성화
  swcMinify: true,
  
  // 실험적 기능
  experimental: {
    // 최적화된 패키지 임포트
    optimizePackageImports: [
      'monaco-editor',
      '@monaco-editor/react',
    ],
  },
  
  // Webpack 설정
  webpack: (config, { isServer, dev }) => {
    // 프로덕션 빌드 최적화
    if (!dev && !isServer) {
      // Monaco Editor 최적화 (필요한 언어만 포함)
      config.resolve.alias = {
        ...config.resolve.alias,
        // Monaco Editor 워커 최적화
        'monaco-editor': 'monaco-editor/esm/vs/editor/editor.api',
      };
      
      // 청크 분할 최적화
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          ...config.optimization.splitChunks,
          cacheGroups: {
            ...config.optimization.splitChunks?.cacheGroups,
            // Monaco Editor 별도 청크
            monaco: {
              test: /[\\/]node_modules[\\/]monaco-editor[\\/]/,
              name: 'monaco',
              chunks: 'async',
              priority: 30,
            },
            // React/Next.js 공통 청크
            framework: {
              test: /[\\/]node_modules[\\/](react|react-dom|next)[\\/]/,
              name: 'framework',
              chunks: 'all',
              priority: 20,
            },
            // 기타 라이브러리
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: 'vendor',
              chunks: 'async',
              priority: 10,
            },
          },
        },
      };
    }
    
    return config;
  },
  
  // 헤더 설정 (보안)
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
    ];
  },
  
  // 리다이렉트
  async redirects() {
    return [];
  },
  
  // 리라이트 (API 프록시)
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = withBundleAnalyzer(nextConfig);
