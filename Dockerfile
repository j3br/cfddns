FROM python:alpine AS base

FROM base AS dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM base AS release

WORKDIR /
COPY --from=dependencies /root/.local /root/.local

WORKDIR /app
COPY cfddns/ /app/cfddns/
COPY docker/start.sh /app/

RUN chmod +x /app/start.sh

CMD ["sh", "-c", "/app/start.sh"]
