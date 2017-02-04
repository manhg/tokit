#!/bin/sh
TOKIT_VER=${TOKIT_VER:=master}
TOKIT_PORT=${TOKIT_PORT:=9000}
TOKIT_ENV=${TOKIT_PORT:=docker}

pip3 install --upgrade https://github.com/manhgd/tokit/archive/$TOKIT_VER.tar.gz

/usr/local/bin/python3 /app/src/app.py --host=0.0.0.0 \
    --port=$TOKIT_PORT --env=$TOKIT_ENV