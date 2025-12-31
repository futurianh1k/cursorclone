FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml /app/
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir -r <(python - <<'PY'
import tomllib
p=tomllib.load(open('pyproject.toml','rb'))
print('\n'.join(p['project']['dependencies']))
PY
) || true
COPY src /app/src
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
