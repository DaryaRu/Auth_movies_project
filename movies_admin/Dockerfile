FROM python:3.10

WORKDIR /opt/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV UWSGI_PROCESSES 1
ENV UWSGI_THREADS 16
ENV UWSGI_HARAKIRI 240
ENV DJANGO_SETTINGS_MODULE 'config.settings'

COPY requirements.txt requirements.txt
COPY uwsgi/uwsgi.ini uwsgi.ini

RUN apt-get update && apt-get install -y gettext && rm -rf /var/lib/apt/lists/*

RUN  mkdir -p /opt/app/media/ \
     && mkdir -p /opt/app/static \
     && mkdir -p /var/wwww/media \
     && mkdir -p /var/wwww/static \
     && pip install --upgrade pip \
     && pip install -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput && \
    python manage.py compilemessages

EXPOSE 8000

RUN groupadd app-group && useradd -G app-group app-user
USER app-user
