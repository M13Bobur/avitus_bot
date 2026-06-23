#!/bin/sh
# Retry pip installs on slow/unstable networks (used inside Docker build).
set -e

MAX_ATTEMPTS="${PIP_BUILD_ATTEMPTS:-5}"
TIMEOUT="${PIP_DEFAULT_TIMEOUT:-1000}"

pip_install() {
  attempt=1
  while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
    echo "pip install attempt $attempt/$MAX_ATTEMPTS: $*"
    if pip install --no-cache-dir --timeout "$TIMEOUT" "$@"; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 10
  done
  return 1
}

pip_install "numpy>=1.26.4,<2.0"
pip_install asyncpg==0.30.0
pip_install pandas==2.2.3
pip_install -r requirements.txt
