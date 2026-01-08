# ============================================================
# 커스텀 code-server 이미지
# Tabby + Continue 확장 사전 설치
# ============================================================
FROM codercom/code-server:latest

# 메타데이터
LABEL maintainer="cursor-onprem-poc"
LABEL description="code-server with Tabby and Continue extensions"

# 시스템 패키지 설치
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    python3 \
    python3-pip \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# coder 사용자로 전환
USER coder
WORKDIR /home/coder

# ============================================================
# VS Code 확장 프로그램 설치
# ============================================================

# Tabby 자동완성 확장
RUN code-server --install-extension TabbyML.vscode-tabby || true

# Continue AI 채팅 확장
RUN code-server --install-extension Continue.continue || true

# 기본 개발 확장들
RUN code-server --install-extension ms-python.python || true
RUN code-server --install-extension dbaeumer.vscode-eslint || true
RUN code-server --install-extension esbenp.prettier-vscode || true
RUN code-server --install-extension PKief.material-icon-theme || true

# ============================================================
# 설정 파일 복사
# ============================================================

# 필요한 디렉토리 생성
RUN mkdir -p /home/coder/.local/share/code-server/User \
    && mkdir -p /home/coder/.config/tabby \
    && mkdir -p /home/coder/.continue

# VS Code 사용자 설정
COPY --chown=coder:coder settings.json /home/coder/.local/share/code-server/User/settings.json

# Tabby 설정
COPY --chown=coder:coder tabby-settings.json /home/coder/.config/tabby/settings.json

# Continue AI 설정
COPY --chown=coder:coder continue/config.json /home/coder/.continue/config.json

# ============================================================
# 환경변수
# ============================================================
ENV TABBY_API_ENDPOINT=http://cursor-poc-gateway:8081
ENV VLLM_API_ENDPOINT=http://cursor-poc-gateway:8081/v1

# 포트 노출
EXPOSE 8080

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
    CMD curl -f http://localhost:8080/healthz || exit 1

# 시작 엔트리포인트(오프라인 VSIX 자동 설치 지원)
# - docker SDK에서 command로 ["--auth","none","--bind-addr","0.0.0.0:8080"] 형태의 args를 넘긴다.
# - 따라서 ENTRYPOINT는 wrapper만 두고, 실제 code-server args는 command로 전달받는다.
COPY --chown=coder:coder entrypoint.sh /usr/local/bin/cursor-entrypoint
RUN chmod +x /usr/local/bin/cursor-entrypoint
ENTRYPOINT ["/usr/local/bin/cursor-entrypoint"]
