#!/bin/sh

export PYTHONPATH=/app:/app/tests

pip install -r /app/tests/functional/requirements.txt --quiet

python3 /app/tests/functional/utils/wait_for_pg.py

if [ "$DEBUG" = "1" ]; then
    pip install debugpy --quiet
    python3 -m debugpy --listen 0.0.0.0:5678 --wait-for-client \
        -m pytest /app/tests/functional/src -c /app/tests/functional/pytest.ini -v
else
    pytest /app/tests/functional/src -c /app/tests/functional/pytest.ini -vv -s
fi