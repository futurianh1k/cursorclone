/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  // Docker 환경에서 정적 파일 서빙을 위한 설정
  images: {
    unoptimized: true,
  },
}

module.exports = nextConfig
