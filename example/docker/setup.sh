set -ex

adduser --system --no-create-home --disabled-password --disabled-login --shell /bin/sh py

VER='3.6.1'
LANG="C.UTF-8"

DEV='cmake gcc make libreadline-dev ncurses-dev libssl-dev zlib1g-dev libpq-dev libev-dev libsass-dev libbz2-dev libsqlite3-dev'
TOOLS='git curl nodejs wget vim ca-certificates'

apt-get update > /dev/null

apt-get install -y \
    $DEV $TOOLS --no-install-recommends > /dev/null

cd /tmp
wget --no-verbose --no-check-certificate \
        https://www.python.org/ftp/python/$VER/Python-$VER.tgz

tar xzf Python-$VER.tgz
cd Python-$VER
./configure  > /dev/null
make  > /dev/null
make install  > /dev/null

rm -rf /var/lib/apt/lists/*
rm -rf /tmp/Python-*