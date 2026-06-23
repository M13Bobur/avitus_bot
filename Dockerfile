FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    gfortran \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# numpy 2.x wheels require X86_V2; pin 1.x for older/emulated CPUs
RUN pip install --no-cache-dir "numpy>=1.26.4,<2.0" \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

RUN chmod +x docker-entrypoint.sh

CMD ["./docker-entrypoint.sh"]
