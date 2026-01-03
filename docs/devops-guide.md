# DevOps 가이드

**작성일**: 2025-01-02  
**목적**: CI/CD, 배포, 모니터링 가이드

---

## 1. CI/CD 파이프라인

### GitHub Actions

프로젝트는 GitHub Actions를 사용하여 CI/CD를 자동화합니다.

#### CI 워크플로우 (`.github/workflows/ci.yml`)

- **트리거**: `main`, `develop` 브랜치에 push 또는 PR
- **작업**:
  1. 코드 체크아웃
  2. Node.js 및 Python 환경 설정
  3. 의존성 설치
  4. 프론트엔드 린트 및 빌드
  5. 백엔드 린트 및 테스트
  6. Docker 이미지 빌드 및 푸시 (main 브랜치만)

#### CD 워크플로우 (`.github/workflows/cd.yml`)

- **트리거**: `main` 브랜치에 push 또는 버전 태그
- **작업**:
  1. 배포 아티팩트 생성
  2. GitHub Release 생성 (태그가 있는 경우)

---

## 2. Docker 배포

### 개발 환경

```bash
# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 중지
docker-compose down
```

### 프로덕션 환경

```bash
# 프로덕션 배포
docker-compose -f docker-compose.prod.yml up -d

# 또는 스크립트 사용
./scripts/deploy.sh production deploy
```

### Makefile 사용

```bash
# 빌드
make build

# 시작
make up

# 중지
make down

# 로그
make logs

# 정리
make clean
```

---

## 3. Kubernetes 배포

### 사전 요구사항

- Kubernetes 클러스터 (1.24+)
- kubectl 설치 및 구성
- PersistentVolume 지원

### 배포 단계

1. **네임스페이스 생성**
   ```bash
   kubectl apply -f k8s/namespace.yaml
   ```

2. **시크릿 생성**
   ```bash
   # secrets.yaml.example을 참고하여 secrets.yaml 생성
   kubectl apply -f k8s/secrets.yaml
   ```

3. **데이터베이스 배포**
   ```bash
   kubectl apply -f k8s/postgres.yaml
   kubectl apply -f k8s/redis.yaml
   ```

4. **애플리케이션 배포**
   ```bash
   kubectl apply -f k8s/api.yaml
   kubectl apply -f k8s/web.yaml
   ```

5. **배포 스크립트 사용**
   ```bash
   ./scripts/k8s-deploy.sh deploy
   ```

### 상태 확인

```bash
# 전체 상태
kubectl get all -n cursor-poc

# Pod 상태
kubectl get pods -n cursor-poc

# 로그 확인
kubectl logs -f deployment/api -n cursor-poc
```

### 자동 스케일링

HPA (Horizontal Pod Autoscaler)가 설정되어 있습니다:

- **API**: CPU 70%, Memory 80% 기준, 3-10 replicas
- **Web**: CPU 70% 기준, 2-5 replicas

---

## 4. 모니터링

### Prometheus & Grafana

모니터링 서비스를 시작하려면:

```bash
docker-compose --profile monitoring up -d prometheus grafana
```

또는:

```bash
make monitoring
```

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)

### Portainer (Docker 관리 UI)

Portainer는 Docker 컨테이너를 시각적으로 관리할 수 있는 웹 UI입니다.

```bash
# Portainer 시작
docker-compose up -d portainer

# 또는 Makefile 사용
make portainer
```

- **Portainer**: http://localhost:9000
- 초기 설정 시 관리자 계정을 생성합니다

### 관리 도구 한번에 시작

```bash
# Portainer와 Grafana 함께 시작
make tools
```

### 메트릭 수집

- API 서버 헬스체크
- 데이터베이스 연결 상태
- Redis 연결 상태
- 리소스 사용량 (CPU, Memory)

---

## 5. 데이터베이스 마이그레이션

### 자동 마이그레이션

애플리케이션 시작 시 자동으로 테이블이 생성됩니다.

### 수동 마이그레이션

```bash
# 마이그레이션 실행
./scripts/migrate-db.sh up

# 또는 Makefile 사용
make migrate
```

---

## 6. 환경변수 설정

### 개발 환경

`.env` 파일을 생성하고 필요한 값들을 설정하세요:

```bash
cp .env.example .env
# .env 파일 편집
```

### 프로덕션 환경

환경변수는 다음 방법으로 설정할 수 있습니다:

1. **Docker Compose**: `docker-compose.yml`의 `environment` 섹션
2. **Kubernetes**: `k8s/secrets.yaml` 및 `k8s/api.yaml`의 `env` 섹션
3. **환경변수 파일**: `.env` 파일 (로컬 개발용)

### 필수 환경변수

- `DATABASE_URL`: PostgreSQL 연결 문자열
- `REDIS_URL`: Redis 연결 문자열
- `JWT_SECRET_KEY`: JWT 토큰 서명 키 (최소 32자)
- `MASTER_ENCRYPTION_KEY`: 암호화 마스터 키 (Fernet 키)

---

## 7. 배포 체크리스트

### 배포 전

- [ ] 환경변수 설정 확인
- [ ] 데이터베이스 백업 (프로덕션)
- [ ] 시크릿 키 확인 및 업데이트
- [ ] Docker 이미지 태그 확인
- [ ] 리소스 제한 확인

### 배포 후

- [ ] 헬스체크 확인 (`/health` 엔드포인트)
- [ ] 로그 확인 (에러 없음)
- [ ] 데이터베이스 연결 확인
- [ ] Redis 연결 확인
- [ ] 모니터링 대시보드 확인

---

## 8. 트러블슈팅

### 컨테이너가 시작되지 않음

```bash
# 로그 확인
docker-compose logs api
docker-compose logs web

# 컨테이너 상태 확인
docker-compose ps
```

### 데이터베이스 연결 실패

```bash
# PostgreSQL 상태 확인
docker-compose exec postgres pg_isready

# 연결 테스트
docker-compose exec postgres psql -U postgres -d cursor_poc
```

### Kubernetes Pod가 시작되지 않음

```bash
# Pod 이벤트 확인
kubectl describe pod <pod-name> -n cursor-poc

# 로그 확인
kubectl logs <pod-name> -n cursor-poc
```

---

## 9. 참고 자료

- [Docker Compose 문서](https://docs.docker.com/compose/)
- [Kubernetes 문서](https://kubernetes.io/docs/)
- [Prometheus 문서](https://prometheus.io/docs/)
- [Grafana 문서](https://grafana.com/docs/)
