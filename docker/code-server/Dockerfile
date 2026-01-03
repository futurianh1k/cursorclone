# VDE Web IDE - code-server 기반 사용자별 IDE 컨테이너
# 용도: 브라우저 기반 VS Code + AI 코딩 확장
# 참조: docs/claudeaivdedev/scaffold/configs/

FROM codercom/code-server:4.96.4

# =============================================
# 시스템 패키지 설치
# =============================================
USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    build-essential \
    openssh-client \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Node.js LTS 업그레이드 (필요시)
# RUN npm install -g n && n lts

# =============================================
# 확장 프로그램 사전 설치
# =============================================
USER coder

# AI 코딩 확장
RUN code-server --install-extension TabbyML.vscode-tabby || true \
    && code-server --install-extension Continue.continue || true

# 언어 지원 확장
RUN code-server --install-extension ms-python.python || true \
    && code-server --install-extension ms-python.black-formatter || true \
    && code-server --install-extension dbaeumer.vscode-eslint || true \
    && code-server --install-extension esbenp.prettier-vscode || true

# 유틸리티 확장
RUN code-server --install-extension eamodio.gitlens || true \
    && code-server --install-extension mhutchie.git-graph || true \
    && code-server --install-extension PKief.material-icon-theme || true

# =============================================
# 설정 파일 복사
# =============================================
# VS Code 설정
COPY --chown=coder:coder settings.json /home/coder/.local/share/code-server/User/settings.json

# Continue 확장 설정
RUN mkdir -p /home/coder/.continue
COPY --chown=coder:coder continue-config.json /home/coder/.continue/config.json

# =============================================
# 환경 변수
# =============================================
ENV SHELL=/bin/bash
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Tabby 서버 엔드포인트 (컨테이너 생성 시 오버라이드)
ENV TABBY_ENDPOINT=http://cursor-poc-tabby:8080
# LiteLLM 엔드포인트
ENV LITELLM_ENDPOINT=http://cursor-poc-litellm:4000

# =============================================
# 포트 및 헬스체크
# =============================================
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

# =============================================
# 시작 명령
# =============================================
# 기본 비밀번호는 환경변수로 전달 (PASSWORD)
ENTRYPOINT ["dumb-init", "code-server", "--bind-addr", "0.0.0.0:8080", "--auth", "password"]
CMD ["/home/coder/workspace"]
