# Production static resource building
# Currently moved to makefile for development

# FROM node:lts-buster-slim AS jsdeps

# RUN apt-get update -y --fix-missing
# RUN apt-get install -y g++ build-essential python3 libmagic1

# COPY . .

# RUN npm install && npm run build

############################################################

FROM python:3.12-bookworm

LABEL maintainer="webops@digital.trade.gov.uk"

ARG ENV="prod"
ENV ENV="${ENV}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1\
    PATH="${PATH}:/home/tamato/.local/bin"

# don't run as root
RUN groupadd -g 1000 tamato && \
    useradd -u 1000 -g tamato -m tamato

WORKDIR /app

# add git client
RUN apt-get -qq update && apt-get install --no-install-recommends -qqy \
    curl \
    ca-certificates \
    git

# fix permissions
RUN chown -R 1000:1000 /app

# install python dependencies
COPY requirements*.txt /app/
RUN pip install --upgrade pip
# Only install dev requirements in dev do not want to expose build tools in production
# RUN  if [ "${ENV}" == "dev" ]; then \
#     pip install -r requirements-dev.txt --no-warn-script-location ; \
#     else pip install -r requirements.txt --no-warn-script-location ; fi
RUN pip install -r requirements-dev.txt --no-warn-script-location

# Copying an empty file works while the directory is mounted as a volume.
COPY --chown=tamato:tamato . /app/
# For production image
# COPY --chown=tamato:tamato --from=jsdeps node_modules/govuk-frontend/govuk node_modules/govuk-frontend/govuk
# COPY --chown=tamato:tamato --from=jsdeps node_modules/chart.js/dist node_modules/chart.js/dist
# COPY --chown=tamato:tamato --from=jsdeps node_modules/moment/min node_modules/moment/min
# COPY --chown=tamato:tamato --from=jsdeps node_modules/chartjs-adapter-moment/dist node_modules/chartjs-adapter-moment/dist
# COPY --chown=tamato:tamato --from=jsdeps static/webpack_bundles static/webpack_bundles
# COPY --chown=tamato:tamato --from=jsdeps webpack-stats.json /app/

USER tamato

EXPOSE 8000

CMD ["/home/tamato/.local/bin/gunicorn", "-b", "0.0.0.0:8000", "-w", "1", "wsgi:application"]
