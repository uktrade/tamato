FROM python:3.8-slim-buster

LABEL maintainer="webops@digital.trade.gov.uk"

ENV DJANGO_SETTINGS_MODULE "settings"

# don't run as root
RUN groupadd -g 1000 tamato && \
    useradd -u 1000 -g tamato -m tamato
USER tamato

WORKDIR /home/tamato

# install python dependencies
COPY requirements.txt ./
RUN pip install -U pip && \
    pip install -r requirements.txt --no-warn-script-location

COPY . .

# empty .env file to prevent warning messages
RUN touch .env

# collect static files for deployment
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["/home/tamato/.local/bin/gunicorn", "-b", "0.0.0.0:8000", "-w", "1", "wsgi:application"]
