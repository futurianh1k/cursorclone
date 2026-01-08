# 0028 - 대화/작업 기록(요약 + 해시)

> 보안 원칙: 프롬프트/응답 원문을 저장하지 않습니다. 필요 시 **해시 + 메타데이터**만 기록합니다.

## 사용자 요청(요약)

- 무거운 code-server 이미지(오프라인 toolchain 포함) 버전을 레포에 추가

## 사용자 요청 원문 해시

- sha256: `4ae58e91164b63ca5154d14b671fd86d80599ef709f7359043ab8fa4ac659279`

## Assistant가 수행한 작업(요약)

- `docker/code-server/Dockerfile.heavy` 추가(offline/debs/*.deb 번들로 dpkg 설치)
- `docker-compose.yml`에 `code-server-builder-heavy` 추가 및 태그 분리
- `docs/0028-code-server-heavy-image.md`에 빌드/전환/검증 절차 문서화
- 최소 테스트 1개 추가(산출물 존재 검증)

