FROM python:3.12-slim AS builder
WORKDIR /src
COPY model/requirements.txt model/requirements.txt
COPY api/requirements.txt api/requirements.txt
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r api/requirements.txt

FROM python:3.12-slim
WORKDIR /srv
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1
COPY --from=builder /opt/venv /opt/venv
COPY api/main.py api/__init__.py ./api/
COPY model/model-1.0.0.joblib ./model/
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=4s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health',timeout=3)"
CMD ["uvicorn","api.main:app","--host","0.0.0.0","--port","8000"]
