#!/bin/bash
set -ex
curl https://raw.githubusercontent.com/stylus/stylus-lang.com/gh-pages/try/stylus.min.js -s \
    -o stylus.js

curl http://coffeescript.org/v1/browser-compiler/coffee-script.js -s \
    -o coffee-script.js

curl https://cdnjs.cloudflare.com/ajax/libs/babel-standalone/6.22.1/babel.min.js -s \
    -o babel.js

curl https://raw.githubusercontent.com/riot/riot/v3.6.1/riot%2Bcompiler.min.js -s \
    -o riot-compiler.js

curl https://raw.githubusercontent.com/riot/riot/v3.6.1/riot.min.js -s \
    -o ../../example/src/riot.js

echo "Done"