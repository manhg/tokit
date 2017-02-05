set -ex

adduser --system --no-create-home --disabled-password --disabled-login --shell /bin/sh py

VER='3.6.0'
LANG="C.UTF-8"

DEV=' gcc make libreadline-dev ncurses-dev libssl-dev zlib1g-dev libpq-dev libev-dev libsass-dev cmake swing libbz2-dev libsqlite3-dev'
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
pip3 install --no-cache-dir -r /tmp/requirements.txt

rm -rf /tmp/Python-$VER
rm -rf /var/lib/apt/lists/*
apt-get -y remove $DEV

chmod 755 /usr/bin/wait-for-it.sh