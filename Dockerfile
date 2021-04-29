FROM node:16-alpine as frontend

COPY server/frontend /src
WORKDIR /src

RUN npm install
RUN npm run production

FROM python:3.8

# Embed full source code
COPY . /src/

# Retrieve previous Javascript build
COPY --from=frontend /src/dist/ /srv/server/frontend/dist/

# Install dependencies
RUN pip install -q /src -r /src/server/requirements3.0.txt -r /src/server/requirements-docker.txt

# Use settings with environment variable support
ENV DJANGO_SETTINGS_MODULE "server.settings_env"

WORKDIR /src/server

# Run with gunicorn, using container's port 80
ENV PORT 80
EXPOSE 80
CMD ["gunicorn", "--bind", "0.0.0.0:80", "server.wsgi"]
