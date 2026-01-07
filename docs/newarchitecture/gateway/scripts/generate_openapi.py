import json
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app

OUT = Path(__file__).resolve().parents[1] / "openapi" / "openapi.json"

def main():
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"generated: {OUT}")

if __name__ == "__main__":
    main()
