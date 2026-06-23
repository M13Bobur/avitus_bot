FROM python:3.12-slim

WORKDIR /app

ENV PIP_DEFAULT_TIMEOUT=1000 \
    PIP_RETRIES=15 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_BUILD_ATTEMPTS=5

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    gfortran \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt scripts/docker_build_slow.sh ./
RUN chmod +x docker_build_slow.sh \
    && ./docker_build_slow.sh

COPY . .

ENV PYTHONPATH=/app

RUN chmod +x docker-entrypoint.sh

CMD ["./docker-entrypoint.sh"]
