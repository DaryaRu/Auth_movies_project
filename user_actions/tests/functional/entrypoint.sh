#!/bin/sh

export PYTHONPATH=$PYTHONPATH=/app:/app/user_actions

pip install -r user_actions/tests/functional/requirements.txt --quiet

python3 user_actions/tests/functional/utils/wait_for_pg.py
python3 user_actions/tests/functional/utils/wait_for_redis.py

if [ "$DEBUG" = "1" ]; then
    pip install debugpy --quiet
    python3 -m debugpy --listen 0.0.0.0:5678 --wait-for-client \
        -m pytest user_actions/tests/functional/src -c user_actions/tests/functional/pytest.ini -v
else
    pytest user_actions/tests/functional/src -c user_actions/tests/functional/pytest.ini -vv -s
fi
