#!/bin/sh

export PYTHONPATH=/app:/app/tests/functional

pip install -r /app/tests/functional/requirements.txt --quiet

if [ "$DEBUG" = "1" ]; then
    pip install debugpy --quiet
    python3 -m debugpy --listen 0.0.0.0:5678 --wait-for-client \
        -m pytest /app/tests/functional/src -c /app/tests/functional/pytest.ini -v
else
    pytest /app/tests/functional/src -c /app/tests/functional/pytest.ini -vv -s
fi
