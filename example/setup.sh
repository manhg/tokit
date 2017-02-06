set -ex

adduser --system --no-create-home --disabled-password --disabled-login --shell /bin/sh py

VER='3.6.0'
LANG="C.UTF-8"

DEV='git curl cmake gcc make libreadline-dev ncurses-dev libssl-dev'
DEV="$DEV zlib1g-dev libpq-dev libev-dev libsass-dev libbz2-dev libsqlite3-dev"
TOOLS='nodejs wget vim ca-certificates'

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
rm Python-$VER

chmod 755 /usr/bin/wait-for-it.sh