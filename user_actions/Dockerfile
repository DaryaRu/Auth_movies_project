ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/tests

COPY user_actions/requirements.txt /app/src/requirements.txt
COPY user_actions/tests/functional/requirements.txt /app/tests/functional/requirements.txt

RUN pip install --upgrade pip \
    && pip install -r /app/src/requirements.txt \
    && pip install -r /app/tests/functional/requirements.txt

COPY user_actions/src/ /app/src/
COPY user_actions/migrations/ /app/migrations/
COPY user_actions/tests/ /app/tests/
