#!/bin/sh

export PYTHONPATH=$PYTHONPATH:/app:/app/analytics

pip install -r analytics/tests/functional/requirements.txt --quiet

python3 analytics/tests/functional/utils/wait_for_redis.py

if [ "$DEBUG" = "1" ]; then
    pip install debugpy --quiet
    python3 -m debugpy --listen 0.0.0.0:5678 --wait-for-client \
        -m pytest analytics/tests/functional/src -c analytics/tests/functional/pytest.ini -v
else
    pytest analytics/tests/functional/src -c analytics/tests/functional/pytest.ini -vv -s
fi
