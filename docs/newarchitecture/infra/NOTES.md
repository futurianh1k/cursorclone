# Infra Notes (v0.3)

- mTLS는 서비스 메시(예: Istio/Linkerd) 또는 앱 레벨(client cert) 중 하나로 표준화 필요.
- UPSTREAM_AUTH_MODE=mtls 사용 시 Secret로 cert/key/ca를 마운트하고 환경변수로 경로 지정.
- OpenAPI verify script는 CI 단계에서 실행하여 drift를 차단.
