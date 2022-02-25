FROM node:16-alpine as frontend

COPY server/frontend /src
WORKDIR /src

RUN npm install
RUN npm run production

FROM python:3.8

# Install dependencies before copying src, so pip is only run when needed
COPY ./requirements.txt ./setup.cfg /src/
RUN cd /src && \
   python -c "from setuptools.config import read_configuration as C; from itertools import chain; o=C('setup.cfg')['options']; ex=o['extras_require']; print('\0'.join(chain(o['install_requires'], ex['docker'], ex['server'], ex['taskmanager'])))" | xargs -0 pip install -q -c requirements.txt && \
   rm -rf /src

# Embed full source code
COPY . /src/

# Retrieve previous Javascript build
COPY --from=frontend /src/dist/ /src/server/frontend/dist/

# Install FM
# Note: the extras must be duplicated above in the Python
#       script to pre-install dependencies.
RUN pip install -q /src[docker,server,taskmanager]

# Use a custom settings file that can be overwritten
ENV DJANGO_SETTINGS_MODULE "server.settings_docker"

WORKDIR /src/server

# Collect staticfiles, including Vue.js build
RUN python manage.py collectstatic --no-input

# Run with gunicorn, using container's port 80
ENV PORT 80
EXPOSE 80
CMD ["gunicorn", "--bind", "0.0.0.0:80", "--access-logfile", "-", "server.wsgi"]
