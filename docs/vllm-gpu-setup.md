# vLLM GPU 설정 가이드

## 문제 상황
Docker가 NVIDIA GPU를 인식하지 못하는 경우 다음 에러가 발생합니다:
```
Error response from daemon: could not select device driver "nvidia" with capabilities: [[gpu]]
```

## 해결 방법

### 1. nvidia-container-toolkit 설치

#### Ubuntu/Debian
```bash
# 저장소 추가
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# 설치
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Docker 데몬 재시작
sudo systemctl restart docker
```

#### WSL2 환경
```bash
# WSL2에서는 추가 설정 필요
# 1. nvidia-container-toolkit 설치 (위와 동일)
# 2. Docker Desktop에서 GPU 지원 활성화 확인
```

### 2. Docker 설정 확인

```bash
# Docker가 GPU를 인식하는지 확인
docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi
```

성공하면 GPU 정보가 출력됩니다.

### 3. vLLM 서버 시작

```bash
cd /home/ubuntu/projects/cursorclone
docker compose --profile gpu up -d vllm

# 상태 확인
docker compose ps vllm
docker compose logs vllm --tail 50
```

### 4. API 서버에서 연결 확인

```bash
# API 컨테이너에서 vLLM 연결 테스트
docker compose exec api python -c "
import httpx
import asyncio

async def test():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get('http://cursor-poc-vllm:8000/health', timeout=5.0)
            print(f'✅ vLLM 연결 성공: {resp.status_code}')
            print(resp.text)
    except Exception as e:
        print(f'❌ vLLM 연결 실패: {e}')

asyncio.run(test())
"
```

## 임시 해결책: DEV_MODE 활성화

GPU 설정이 어려운 경우, DEV_MODE를 활성화하여 Mock 응답을 사용할 수 있습니다:

```bash
# docker-compose.yml에서 API 서비스의 DEV_MODE를 true로 변경
# 또는 환경변수로 설정
export DEV_MODE=true
docker compose up -d api
```

주의: DEV_MODE에서는 실제 AI 기능이 동작하지 않고 Mock 응답만 반환됩니다.

