FROM node:lts-buster-slim AS jsdeps

RUN apt-get update -y
RUN apt-get install -y g++ build-essential python3

COPY . .

RUN npm install && npm run build


FROM python:3.8-slim-buster

LABEL maintainer="webops@digital.trade.gov.uk"

ENV DJANGO_SETTINGS_MODULE "settings"

# add git client
RUN apt-get -qq update && apt-get install --no-install-recommends -qqy \
    curl \
    ca-certificates \
    git

# don't run as root
RUN groupadd -g 1000 tamato && \
    useradd -u 1000 -g tamato -m tamato

WORKDIR /home/tamato/app

# Extend PATH for dev ease-of-use and to stop pip complaining.
ENV PATH="${PATH}:/home/tamato/.local/bin"

# install python dependencies
COPY requirements.txt ./
RUN pip install -U pip && \
    pip install -r requirements.txt --no-warn-script-location

# Copying an empty file works while the directory is mounted as a volume.
COPY --chown=tamato:tamato .empty .env
COPY --chown=tamato:tamato . .
COPY --chown=tamato:tamato --from=jsdeps node_modules/govuk-frontend/govuk node_modules/govuk-frontend/govuk
COPY --chown=tamato:tamato --from=jsdeps static/webpack_bundles static/webpack_bundles
COPY --chown=tamato:tamato --from=jsdeps webpack-stats.json ./

# collect static files for deployment
RUN python manage.py collectstatic --noinput

USER tamato

EXPOSE 8000
CMD ["/home/tamato/.local/bin/gunicorn", "-b", "0.0.0.0:8000", "-w", "1", "wsgi:application"]
