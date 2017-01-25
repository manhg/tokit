FROM debian:stretch-slim

ENV PATH /usr/local/bin:$PATH
ENV PYTHONUNBUFFERED 1
ENV LANG C.UTF-8
COPY requirements.txt /tmp/req.txt
COPY requirements_extra.txt /tmp/req.txt
RUN set -ex \

    # declare
    && VER='3.6.0' \
    && DEV=' gcc make libreadline-dev ncurses-dev \
        libssl-dev zlib1g-dev libpq-dev libev-dev' \
    && TOOLS='nodejs wget vim ca-certificates ' \

    && apt-get update && apt-get install -y \
        $DEV $TOOLS --no-install-recommends > /dev/null \
    && rm -rf /var/lib/apt/lists/* \

    # install Python
    && cd /tmp \
    && wget --no-verbose --no-check-certificate \
            https://www.python.org/ftp/python/$VER/Python-$VER.tgz \
    && tar xzf Python-$VER.tgz && cd Python-$VER \
    && ./configure  > /dev/null \
    && make  > /dev/null \
    && make install  > /dev/null \

    # install packages
    && CCFLAGS=-fPIC scons arch=x64 \
    && pip3 install --no-cache-dir -r /tmp/req.txt \

    # clean up
    && rm -rf /tmp/Python-$VER \
    && apt-get -y remove $DEV

CMD ["python3"]