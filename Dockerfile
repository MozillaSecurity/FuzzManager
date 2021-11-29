FROM node:16-alpine as frontend

COPY server/frontend /src
WORKDIR /src

RUN npm install
RUN npm run production

FROM python:3.8

# Install dependencies before copying src, so pip is only run when needed
COPY ./server/requirements3.0.txt ./server/requirements-docker.txt /tmp/
RUN pip install -q -r /tmp/requirements3.0.txt -r /tmp/requirements-docker.txt

# Embed full source code
COPY . /src/

# Retrieve previous Javascript build
COPY --from=frontend /src/dist/ /src/server/frontend/dist/

# Install FM
RUN pip install -q /src

# Use a custom settings file that can be overwritten
ENV DJANGO_SETTINGS_MODULE "server.settings_docker"

WORKDIR /src/server

# Collect staticfiles, including Vue.js build
RUN python manage.py collectstatic --no-input

# Run with gunicorn, using container's port 80
ENV PORT 80
EXPOSE 80
CMD ["gunicorn", "--bind", "0.0.0.0:80", "--access-logfile", "-", "server.wsgi"]
