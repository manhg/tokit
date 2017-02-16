#!/bin/sh
TOKIT_VER=${TOKIT_VER:=0.7}
TOKIT_PORT=${TOKIT_PORT:=9000}
TOKIT_ENV=${TOKIT_PORT:=docker}

pip3 install --upgrade tokit==$TOKIT_VER

/usr/local/bin/python3 /app/src/app.py --host=0.0.0.0 \
    --port=$TOKIT_PORT --env=$TOKIT_ENV
