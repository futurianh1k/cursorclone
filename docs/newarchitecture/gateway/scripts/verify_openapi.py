import json
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app

PINNED = Path(__file__).resolve().parents[1] / "openapi" / "openapi.json"

def main():
    client = TestClient(app)
    current = client.get("/openapi.json").json()
    pinned = json.loads(PINNED.read_text(encoding="utf-8"))
    if current != pinned:
        raise SystemExit("OpenAPI drift detected. Run scripts/generate_openapi.py and commit openapi.json")
    print("OpenAPI verified: OK")

if __name__ == "__main__":
    main()
