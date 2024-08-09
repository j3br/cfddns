FROM python:alpine AS base

FROM base AS dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM dependencies AS release

WORKDIR /app

COPY cfddns/ /app/cfddns/
COPY docker/start.sh /app/

RUN chmod +x /app/start.sh

CMD ["sh", "-c", "/app/start.sh"]
