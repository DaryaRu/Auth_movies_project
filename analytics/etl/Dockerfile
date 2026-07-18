FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
COPY __init__.py transformers.py schemas.py main.py loaders.py extractors.py ./
COPY core ./core
COPY db ./db
COPY repositories ./repositories
COPY utils ./utils
COPY monitorings ./monitorings

RUN pip install --no-cache-dir -r requirements.txt

CMD ["faststream", "run", "main:app"]
