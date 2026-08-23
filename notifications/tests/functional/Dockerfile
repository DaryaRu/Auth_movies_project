ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/tests/functional

COPY requirements.txt /app/requirements.txt
COPY tests/functional/requirements.txt /app/tests/functional/requirements.txt

RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt \
    && pip install -r /app/tests/functional/requirements.txt

COPY src/ /app/src/
COPY migrations/ /app/migrations/
COPY tests/ /app/tests/
