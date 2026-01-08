from typing import Optional, Tuple
from .config import settings


def upstream_headers() -> dict:
    mode = settings.upstream_auth_mode
    if mode == "static_bearer":
        if not settings.upstream_bearer_token:
            # misconfig; in prod you may want to fail closed
            return {}
        return {"Authorization": f"Bearer {settings.upstream_bearer_token}"}
    # mtls: handled via httpx client cert/verify settings; no auth header needed
    return {}


def internal_headers(service_name: str) -> dict:
    """
    내부 upstream(auth separation)용 헤더.
    - workspace 사용자 토큰(Authorization)은 upstream으로 전달하지 않는다.
    - 필요한 경우에만 서비스 간 토큰을 별도 헤더로 전달한다.
    """
    if not settings.upstream_internal_token:
        return {}
    if service_name not in {"rag", "agent"}:
        return {}
    return {settings.upstream_internal_token_header: settings.upstream_internal_token}


def httpx_verify_and_cert() -> Tuple[object, Optional[Tuple[str, str]]]:
    # verify can be True/False/path; for mtls we provide CA file and client cert/key
    if settings.upstream_auth_mode == "mtls":
        verify = settings.upstream_ca_file or True
        cert = None
        if settings.upstream_client_cert_file and settings.upstream_client_key_file:
            cert = (settings.upstream_client_cert_file, settings.upstream_client_key_file)
        return verify, cert
    return True, None

