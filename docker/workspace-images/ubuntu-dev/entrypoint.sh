#!/bin/bash
set -e

# SSH 키 설정 (환경변수에서)
if [ -n "$SSH_PUBLIC_KEY" ]; then
    echo "$SSH_PUBLIC_KEY" >> /home/developer/.ssh/authorized_keys
    chmod 600 /home/developer/.ssh/authorized_keys
    chown developer:developer /home/developer/.ssh/authorized_keys
    echo "✅ SSH public key added"
fi

# SSH 비밀번호 설정 (환경변수에서)
if [ -n "$SSH_PASSWORD" ]; then
    echo "developer:$SSH_PASSWORD" | sudo chpasswd
    echo "✅ SSH password set"
fi

# Git 사용자 설정 (환경변수에서)
if [ -n "$GIT_USER_NAME" ]; then
    git config --global user.name "$GIT_USER_NAME"
fi
if [ -n "$GIT_USER_EMAIL" ]; then
    git config --global user.email "$GIT_USER_EMAIL"
fi

# 워크스페이스 권한 설정
if [ -d "/workspace" ]; then
    sudo chown -R developer:developer /workspace 2>/dev/null || true
fi

# Python 가상환경 자동 생성 (선택적)
if [ "$AUTO_VENV" = "true" ] && [ ! -d "/workspace/.venv" ]; then
    python3 -m venv /workspace/.venv
    echo "✅ Python virtual environment created"
fi

# 명령어 처리
case "$1" in
    "ssh")
        echo "🚀 Starting SSH server..."
        sudo /usr/sbin/sshd -D
        ;;
    "dev")
        echo "🔧 Development mode (SSH + keep alive)"
        sudo /usr/sbin/sshd
        exec tail -f /dev/null
        ;;
    *)
        # 사용자 지정 명령어 실행
        exec "$@"
        ;;
esac
