FROM python:3.6.6-slim

MAINTAINER <pjialin admin@pjialin.com>
ENV TZ Asia/Shanghai

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


RUN mkdir -p /data/query /data/user
VOLUME /data

COPY . .

COPY env.docker.py.example /config/env.py

CMD [ "python", "main.py" , "-c", "/config/env.py"]
