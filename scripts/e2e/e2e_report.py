import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _mask_email(email: str) -> str:
    if "@" not in email:
        return email
    user, dom = email.split("@", 1)
    if len(user) <= 2:
        user_mask = user[:1] + "*"
    else:
        user_mask = user[:2] + "*" * (len(user) - 2)
    return f"{user_mask}@{dom}"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def main():
    # Inputs are provided via env to keep bash simple and avoid sensitive leakage.
    out_dir = Path(os.environ.get("E2E_REPORT_DIR", "reports/e2e")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = os.environ.get("E2E_TS") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = os.environ.get("E2E_REPORT_BASENAME", f"whitelabel_e2e_{ts}")

    report = {
        "generated_at_utc": _utc_now(),
        "base_url": os.environ.get("BASE_URL"),
        "api_url": os.environ.get("API_URL"),
        "gateway_url": os.environ.get("GATEWAY_URL"),
        "web_url": os.environ.get("WEB_URL"),
        "test_user": {
            "email_masked": _mask_email(os.environ.get("TEST_EMAIL", "")),
            "org": os.environ.get("TEST_ORG", ""),
        },
        "ids": {
            "project_id": os.environ.get("PROJECT_ID", ""),
            "workspace_id": os.environ.get("WORKSPACE_ID", ""),
            "ide_url": os.environ.get("IDE_URL", ""),
        },
        "checks": json.loads(os.environ.get("E2E_CHECKS_JSON", "{}")),
        "notes": [
            "No passwords or access tokens are stored in this report.",
            "IDE Tabby/Chat UI validation is manual; this report covers API/Gateway reachability and RAG endpoints.",
        ],
    }

    json_path = out_dir / f"{base}.json"
    md_path = out_dir / f"{base}.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Markdown summary (operator-friendly)
    lines = []
    lines.append(f"# White label SaaS E2E Report — {base}")
    lines.append("")
    lines.append(f"- generated_at_utc: `{report['generated_at_utc']}`")
    lines.append(f"- api_url: `{report['api_url']}`")
    lines.append(f"- gateway_url: `{report['gateway_url']}`")
    lines.append(f"- web_url: `{report['web_url']}`")
    lines.append(f"- test_user: `{report['test_user']['email_masked']}` / org `{report['test_user']['org']}`")
    lines.append("")
    lines.append("## IDs")
    lines.append(f"- project_id: `{report['ids']['project_id']}`")
    lines.append(f"- workspace_id: `{report['ids']['workspace_id']}`")
    lines.append(f"- ide_url: `{report['ids']['ide_url']}`")
    lines.append("")
    lines.append("## Checks")
    checks = report["checks"] or {}
    for k in sorted(checks.keys()):
        v = checks[k]
        status = v.get("ok")
        code = v.get("status_code")
        detail = v.get("detail", "")
        lines.append(f"- **{k}**: ok={status} status_code={code} {detail}".rstrip())
    lines.append("")
    lines.append("## Notes")
    for n in report["notes"]:
        lines.append(f"- {n}")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(str(json_path))
    print(str(md_path))


if __name__ == "__main__":
    main()

