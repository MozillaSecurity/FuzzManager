FROM python:3.8

COPY . /src/

RUN pip install /src
RUN pip install -r /src/server/requirements3.0.txt
RUN pip install gunicorn

WORKDIR /src/server

ENV PORT 80
EXPOSE 80
CMD ["gunicorn", "--bind", "0.0.0.0:80", "server.wsgi"]
