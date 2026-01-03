# vLLM 서버 설정 가이드

## 개요

이 프로젝트는 [vLLM](https://github.com/vllm-project/vllm)을 사용하여 AI 코드 분석 기능을 제공합니다.
vLLM은 OpenAI API 호환 엔드포인트를 제공하며, 다양한 오픈소스 LLM을 실행할 수 있습니다.

## 방법 1: 외부 vLLM 서버 연결

이미 실행 중인 vLLM 서버가 있다면:

### 1. 환경변수 설정

```bash
# apps/api/.env 파일 수정
VLLM_BASE_URL=http://your-vllm-server:8000/v1
VLLM_API_KEY=your-api-key  # 필요한 경우
DEV_MODE=false
```

### 2. API 서버 재시작

```bash
docker compose restart api
```

---

## 방법 2: Docker Compose로 vLLM 서버 실행 (GPU 필요)

### 전제 조건

- NVIDIA GPU (CUDA 12.0+)
- nvidia-container-toolkit 설치
- 최소 16GB+ GPU 메모리 (7B 모델 기준)

### 1. nvidia-container-toolkit 설치 (Ubuntu)

```bash
# NVIDIA Container Toolkit 저장소 추가
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Docker 설정
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 2. vLLM 서비스 실행

```bash
cd /home/ubuntu/projects/cursor-onprem-poc

# GPU 확인
nvidia-smi

# vLLM과 함께 실행
docker compose -f docker-compose.yml -f docker-compose.vllm.yml up -d
```

### 3. 모델 변경

기본 모델: `Qwen/Qwen2.5-Coder-7B-Instruct`

다른 모델을 사용하려면:

```bash
# 환경변수로 모델 지정
export VLLM_MODEL=codellama/CodeLlama-7b-Instruct-hf
docker compose -f docker-compose.yml -f docker-compose.vllm.yml up -d
```

**권장 코드 모델**:
| 모델 | 크기 | GPU 메모리 | 설명 |
|------|------|-----------|------|
| `Qwen/Qwen2.5-Coder-7B-Instruct` | 7B | 16GB | 코딩 특화, 다국어 지원 |
| `codellama/CodeLlama-7b-Instruct-hf` | 7B | 16GB | Meta의 코드 LLaMA |
| `deepseek-ai/deepseek-coder-6.7b-instruct` | 6.7B | 16GB | DeepSeek 코더 |
| `mistralai/Mistral-7B-Instruct-v0.3` | 7B | 16GB | 범용 Mistral |

---

## 방법 3: vLLM 직접 설치 (로컬)

Docker 없이 직접 실행:

```bash
# Python 가상환경 생성
python3 -m venv vllm-env
source vllm-env/bin/activate

# vLLM 설치
pip install vllm

# 서버 실행
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --host 0.0.0.0 \
  --port 8001

# API 서버 환경변수 설정
export VLLM_BASE_URL=http://localhost:8001/v1
export DEV_MODE=false
```

---

## 방법 4: OpenAI API 호환 서비스 사용

vLLM 외에도 OpenAI API 호환 서비스를 사용할 수 있습니다:

### Ollama

```bash
# Ollama 설치 및 실행
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &

# 모델 다운로드
ollama pull qwen2.5-coder:7b

# 환경변수 설정
export VLLM_BASE_URL=http://localhost:11434/v1
export DEV_MODE=false
```

### LM Studio

1. [LM Studio](https://lmstudio.ai/) 다운로드
2. 모델 다운로드 및 로드
3. Local Server 시작 (포트 1234)
4. 환경변수 설정:
   ```bash
   export VLLM_BASE_URL=http://localhost:1234/v1
   ```

### OpenAI API (클라우드)

온프레미스가 아닌 경우 OpenAI API도 사용 가능:

```bash
export VLLM_BASE_URL=https://api.openai.com/v1
export VLLM_API_KEY=sk-your-openai-key
export DEV_MODE=false
```

---

## 연결 테스트

```bash
# vLLM 서버 상태 확인
curl http://localhost:8001/health

# 모델 목록 확인
curl http://localhost:8001/v1/models

# 채팅 테스트
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

---

## 문제 해결

### GPU 메모리 부족

```bash
# GPU 메모리 사용량 줄이기
export VLLM_GPU_MEMORY=0.7
export VLLM_MAX_MODEL_LEN=4096
```

### 모델 다운로드 실패

```bash
# HuggingFace 토큰 설정 (일부 모델 필요)
export HF_TOKEN=hf_your_token_here
```

### 연결 실패

```bash
# API 서버 로그 확인
docker compose logs api

# vLLM 서버 로그 확인
docker compose -f docker-compose.yml -f docker-compose.vllm.yml logs vllm
```

---

## 참고 자료

- **vLLM 문서**: https://docs.vllm.ai/
- **vLLM GitHub**: https://github.com/vllm-project/vllm
- **Ollama**: https://ollama.com/
- **HuggingFace Hub**: https://huggingface.co/models
