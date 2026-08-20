FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py render.py consumer.py contacts.py audience.py ./
COPY core ./core
COPY db ./db
COPY repositories ./repositories
COPY senders ./senders

CMD ["faststream", "run", "main:app"]
