FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
COPY __init__.py backoff.py config.py logging_config.py main.py ./
COPY extract ./extract
COPY load ./load
COPY models.py ./models.py
COPY pipeline ./pipeline
COPY transform ./transform
COPY state ./state

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
