#!/bin/sh
python3 /app/tests/functional/utils/wait_for_es.py
python3 /app/tests/functional/utils/wait_for_redis.py

if [ "$DEBUG" = "1" ]; then
    python3 -m debugpy --listen 0.0.0.0:5678 --wait-for-client \
        -m pytest /app/tests/functional/src -c /app/tests/functional/pytest.ini -v
else
    pytest /app/tests/functional/src -c /app/tests/functional/pytest.ini -v
fi
