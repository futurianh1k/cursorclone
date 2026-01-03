# Technical Design Document

## 1. 기술 스택
- IDE: code-server
- Backend: FastAPI
- LLM: vLLM/TGI
- Orchestration: Kubernetes

## 2. 장애 대응
- Gateway 장애 시 IDE Read-only
- LLM 장애 시 대체 모델

## 3. 확장성
- IDE 수평 확장
- GPU Pool 스케줄링