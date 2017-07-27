#!/bin/sh
TOKIT_PORT=${TOKIT_PORT:=9000}
TOKIT_ENV=${TOKIT_PORT:=docker}

pip3 install --upgrade -r /app/src/requirements.txt

/usr/local/bin/python3 /app/src/app.py \
    --host=0.0.0.0 \
    --port=$TOKIT_PORT \
    --env=$TOKIT_ENV
