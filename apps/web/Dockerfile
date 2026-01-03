# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package files
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
# Copy packages package.json files (if packages exist)
COPY packages/ ./packages/

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY apps/web ./apps/web
COPY packages ./packages

# Build
WORKDIR /app/apps/web
RUN pnpm build

# Production stage - Standalone 모드
FROM node:20-alpine AS runner

WORKDIR /app

# 보안: non-root 사용자 생성
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 환경 변수 설정
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Standalone 빌드 결과물 복사
# standalone에는 필요한 node_modules가 포함되어 있음
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public

# Non-root 사용자로 전환
USER nextjs

EXPOSE 3000

# Standalone 서버 실행
# standalone 빌드에서는 server.js가 apps/web/ 경로에 생성됨
CMD ["node", "apps/web/server.js"]
