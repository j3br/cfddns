FROM python:alpine AS base

FROM base AS dependencies
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

FROM dependencies AS release

WORKDIR /app

COPY cfddns/ /app/cfddns/
COPY docker/run.sh docker/start.sh /app/

RUN chmod +x /app/run.sh && \
    chmod +x /app/start.sh

RUN touch /var/log/cron.log

CMD ["sh", "-c", "/app/start.sh"]