FROM python:3.8-slim-buster

LABEL maintainer="andy.driver@digital.trade.gov.uk"

ENV DJANGO_SETTINGS_MODULE "tamato.settings"

# don't run as root
RUN groupadd -g 1000 tamato && \
    useradd -u 1000 -g tamato -m tamato
USER tamato

WORKDIR /home/tamato

# install python dependencies
COPY requirements.txt manage.py ./
RUN python -mvenv venv && \
    venv/bin/pip install -U pip && \
    venv/bin/pip install -r requirements.txt

COPY tamato tamato
COPY docker docker
COPY static static

# empty .env file to prevent warning messages
RUN touch .env

# collect static files for deployment
RUN venv/bin/python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["venv/bin/gunicorn", "-b", "0.0.0.0:8000", "-w", "4", "tamato.wsgi:application"]
