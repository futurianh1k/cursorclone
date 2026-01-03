# Ubuntu 24.04 기반 개발 워크스페이스 이미지
# SSH 서버 포함, 다양한 개발 도구 사전 설치

FROM ubuntu:24.04

LABEL maintainer="cursor-onprem"
LABEL description="Ubuntu 24.04 based development workspace with SSH server"
LABEL version="1.0.0"

# 비대화형 설치 모드
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Seoul

# 기본 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    # SSH 서버
    openssh-server \
    # 기본 도구
    sudo \
    curl \
    wget \
    git \
    vim \
    nano \
    htop \
    tree \
    zip \
    unzip \
    jq \
    ca-certificates \
    gnupg \
    lsb-release \
    locales \
    tzdata \
    # 빌드 도구
    build-essential \
    cmake \
    pkg-config \
    # 네트워크 도구
    net-tools \
    iputils-ping \
    dnsutils \
    # Python
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    # 기타
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 로케일 설정
RUN locale-gen ko_KR.UTF-8 en_US.UTF-8
ENV LANG=ko_KR.UTF-8
ENV LANGUAGE=ko_KR:ko
ENV LC_ALL=ko_KR.UTF-8

# Node.js 20.x LTS 설치
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g pnpm yarn \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Java 21 (OpenJDK) 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-21-jdk \
    maven \
    gradle \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Go 1.22 설치
ENV GO_VERSION=1.22.0
RUN wget -q https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz \
    && rm go${GO_VERSION}.linux-amd64.tar.gz
ENV PATH="${PATH}:/usr/local/go/bin"
ENV GOPATH=/home/developer/go
ENV PATH="${PATH}:${GOPATH}/bin"

# Rust 설치 (선택적 - 이미지 크기 증가)
# RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
# ENV PATH="${PATH}:/root/.cargo/bin"

# SSH 서버 설정
RUN mkdir -p /var/run/sshd \
    && mkdir -p /etc/ssh/sshd_config.d \
    && echo "PasswordAuthentication yes" > /etc/ssh/sshd_config.d/password.conf \
    && echo "PermitRootLogin no" >> /etc/ssh/sshd_config.d/password.conf \
    && echo "PubkeyAuthentication yes" >> /etc/ssh/sshd_config.d/password.conf \
    && echo "AuthorizedKeysFile .ssh/authorized_keys" >> /etc/ssh/sshd_config.d/password.conf \
    && ssh-keygen -A

# 개발자 사용자 생성 (UID 1000)
RUN useradd -m -s /bin/bash -u 1000 developer \
    && echo "developer ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers \
    && mkdir -p /home/developer/.ssh \
    && chmod 700 /home/developer/.ssh \
    && chown -R developer:developer /home/developer

# 작업 디렉토리 설정
WORKDIR /workspace
RUN chown developer:developer /workspace

# Python 기본 패키지 (글로벌)
RUN pip3 install --no-cache-dir --break-system-packages \
    ipython \
    black \
    flake8 \
    mypy \
    pytest \
    httpx \
    requests

# Git 설정
RUN git config --global init.defaultBranch main \
    && git config --global core.editor vim \
    && git config --global pull.rebase false

# 환경 변수
ENV HOME=/home/developer
ENV USER=developer
ENV SHELL=/bin/bash

# SSH 및 애플리케이션 포트
EXPOSE 22 3000 5000 8000 8080

# 시작 스크립트
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 기본 사용자로 전환
USER developer

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# 기본 명령어 (SSH 서버 + 무한 대기)
CMD ["ssh"]
