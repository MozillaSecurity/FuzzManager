FROM node:20-alpine as frontend

COPY server/frontend /src
RUN chown -R node:node /src
USER node
WORKDIR /src

RUN npm install
RUN npm run production

FROM python:3.10-alpine as backend

RUN apk add --no-cache build-base git mariadb-dev

# Install dependencies before copying src, so pip is only run when needed
# Also install build dependencies that are otherwise missed in wheel cache
#   (from pyproject.toml [build-system].requires)
COPY ./requirements.txt ./setup.cfg /src/
RUN cd /src && \
   python -c "from setuptools.config import read_configuration as C; from itertools import chain; o=C('setup.cfg')['options']; ex=o['extras_require']; print('\0'.join(chain(o['install_requires'], ex['docker'], ex['server'], ex['taskmanager'])))" | xargs -0 pip wheel -q -c requirements.txt --wheel-dir /var/cache/wheels && \
   pip wheel -q --wheel-dir /var/cache/wheels wheel setuptools_scm[toml]

FROM python:3.10-alpine

RUN adduser -D worker && \
   apk add --no-cache bash git mariadb-client mariadb-connector-c openssh-client-default && \
   rm -rf /var/log/*

COPY --from=backend /var/cache/wheels /var/cache/wheels

COPY ./requirements.txt ./setup.cfg /src/
USER worker
RUN cd /src && \
   python -c "from setuptools.config import read_configuration as C; from itertools import chain; o=C('setup.cfg')['options']; ex=o['extras_require']; print('\0'.join(chain(o['install_requires'], ex['docker'], ex['server'], ex['taskmanager'])))" | xargs -0 pip install --no-cache-dir --no-index --find-links /var/cache/wheels -q -c requirements.txt

# Embed full source code
USER root
COPY . /src/

# Retrieve previous Javascript build
COPY --from=frontend /src/dist/ /src/server/frontend/dist/
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

# Install FM
# Note: the extras must be duplicated above in the Python
#       script to pre-install dependencies.
USER worker
ENV PATH "${PATH}:/home/worker/.local/bin"
RUN pip install --no-cache-dir --no-index --find-links /var/cache/wheels --no-deps -q /src[docker,server,taskmanager]
RUN mkdir -m 0700 /home/worker/.ssh && cp /src/misc/sshconfig /home/worker/.ssh/config && ssh-keyscan github.com > /home/worker/.ssh/known_hosts

# Use a custom settings file that can be overwritten
ENV DJANGO_SETTINGS_MODULE "server.settings_docker"

WORKDIR /src/server

# Collect staticfiles, including Vue.js build
RUN python manage.py collectstatic --no-input

# Run with gunicorn, using container's port 80
ENV PORT 80
EXPOSE 80
CMD ["gunicorn", "--bind", "0.0.0.0:80", "--access-logfile", "-", "--capture-output", "server.wsgi"]
