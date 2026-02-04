FROM node:20-alpine AS frontend

COPY server/frontend /src
RUN chown -R node:node /src
USER node
WORKDIR /src

RUN npm install
RUN npm run production

FROM python:3.11-alpine

ARG SETUPTOOLS_SCM_PRETEND_VERSION_FOR_FuzzManager
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_FuzzManager=$SETUPTOOLS_SCM_PRETEND_VERSION_FOR_FuzzManager

# Install system dependencies
RUN adduser -D worker && \
    apk add --no-cache bash git mariadb-client mariadb-connector-c openssh-client-default && \
    rm -rf /var/log/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Embed full source code
COPY . /src/

# Retrieve previous Javascript build
COPY --from=frontend /src/dist/ /src/server/frontend/dist/

# Install build dependencies, install FuzzManager, then clean up in single layer
RUN apk add --no-cache --virtual .build-deps build-base linux-headers mariadb-dev && \
    cd /src && \
    UV_PROJECT_ENVIRONMENT=/usr/local uv sync --frozen --extra docker --extra sentry --extra server --extra taskmanager --no-dev && \
    uv cache clean && \
    rm -rf /root/.cache/uv && \
    apk del .build-deps && \
    rm -rf /var/log/*

# Setup directories and permissions
RUN mkdir -p \
      /data/fuzzing-tc-config \
      /data/crashes \
      /data/coverage \
      /data/repos \
      /data/userdata \
   && chown -R worker:worker \
      /src \
      /data/fuzzing-tc-config \
      /data/crashes \
      /data/coverage \
      /data/repos \
      /data/userdata

USER worker
ENV PATH="${PATH}:/home/worker/.local/bin"
RUN mkdir -m 0700 /home/worker/.ssh && cp /src/misc/sshconfig /home/worker/.ssh/config && ssh-keyscan github.com > /home/worker/.ssh/known_hosts

# Use a custom settings file that can be overwritten
ENV DJANGO_SETTINGS_MODULE="server.settings_docker"

WORKDIR /src/server

# Collect staticfiles, including Vue.js build
RUN python manage.py collectstatic --no-input

# Run with gunicorn, using container's port 80
ENV PORT=80
EXPOSE 80
CMD ["gunicorn", "--bind", "0.0.0.0:80", "--access-logfile", "-", "--capture-output", "server.wsgi"]
