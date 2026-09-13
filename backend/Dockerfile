FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt \
    && addgroup --system app \
    && adduser --system --ingroup app app

COPY --chown=app:app backend/app /app/backend/app
COPY --chown=app:app backend/start.py /app/backend/start.py
COPY --chown=app:app backend/__init__.py /app/backend/__init__.py

USER app
EXPOSE 8000

CMD ["python", "-m", "backend.start"]
