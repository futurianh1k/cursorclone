import time
import re
from typing import List, Tuple
import yaml
from .config import settings

class DlpEngine:
    def __init__(self):
        self._loaded_at = 0.0
        self._rules: List[Tuple[str, re.Pattern[bytes], str]] = []
        self._version = "dlp-unknown"
        self.reload(force=True)

    @property
    def version(self) -> str:
        return self._version

    def reload(self, force: bool = False):
        now = time.time()
        if not force and (now - self._loaded_at) < settings.dlp_reload_seconds:
            return
        with open(settings.dlp_rules_path, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
        self._version = str(doc.get("version", "dlp-unknown"))
        rules = []
        for r in (doc.get("rules") or []):
            if r.get("kind") != "regex":
                continue
            rid = str(r.get("id"))
            pat = str(r.get("pattern"))
            action = str(r.get("action", "allow"))
            compiled = re.compile(pat.encode("utf-8"))
            rules.append((rid, compiled, action))
        self._rules = rules
        self._loaded_at = now

    def inspect_bytes(self, b: bytes) -> tuple[str, str | None]:
        self.reload(force=False)
        if not b:
            return ("allow", None)
        for rid, pattern, action in self._rules:
            if pattern.search(b):
                return (action, rid)
        return ("allow", None)

dlp_engine = DlpEngine()
