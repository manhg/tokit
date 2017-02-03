#!/bin/sh
pip3 install --upgrade https://github.com/manhgd/tokit/archive/$TOKIT_VER.tar.gz
/usr/local/bin/python3 /app/src/app.py --host=0.0.0.0 --port=$PORT --env=docker