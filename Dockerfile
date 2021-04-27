FROM python:3.8

# Embed full source code
COPY . /src/

# Setup unprivileged user account
RUN adduser --disabled-password --gecos "" --force-badname --uid 2000 fuzzmanager
RUN chown fuzzmanager /src -R

# Install dependencies
RUN pip install -q /src -r /src/server/requirements3.0.txt gunicorn

# Use settings with environment variable support
ENV DJANGO_SETTINGS_MODULE "server.settings_env"

# Run as fuzzmanager using server's code base
WORKDIR /src/server
USER fuzzmanager

# Run with gunicorn, using container's port 80
ENV PORT 80
EXPOSE 80
CMD ["gunicorn", "--bind", "0.0.0.0:80", "server.wsgi"]
