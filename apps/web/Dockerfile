# Build stage
# NOTE: 외부 네트워크 접근이 제한된 환경에서도 빌드가 가능하도록 digest로 pinning.
FROM node:20-alpine@sha256:658d0f63e501824d6c23e06d4bb95c71e7d704537c9d9272f488ac03a370d448 AS builder

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

# Production stage
#
# NOTE:
# - Next standalone 출력물을 그대로 사용하는 방식은 monorepo(pnpm)에서 생성된 symlink 경로가
#   런타임 경로와 어긋나며('next' 모듈 resolve 실패), 컨테이너가 재시작 루프에 빠질 수 있다.
# - PoC 안정성을 우선하여, 빌드 결과(.next) + node_modules를 포함한 /app 전체를 복사해 next start로 구동한다.
FROM node:20-alpine@sha256:658d0f63e501824d6c23e06d4bb95c71e7d704537c9d9272f488ac03a370d448 AS runner

WORKDIR /app

# 보안: non-root 사용자 생성
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 환경 변수 설정
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# 빌드 산출물 + 의존성 복사 (monorepo symlink 경로 유지)
COPY --from=builder --chown=nextjs:nodejs /app /app

USER nextjs

EXPOSE 3000

WORKDIR /app/apps/web
CMD ["node", "node_modules/next/dist/bin/next", "start", "-p", "3000"]
