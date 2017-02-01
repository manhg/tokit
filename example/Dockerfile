FROM debian:stretch-slim

COPY setup.sh /tmp/setup.sh
COPY requirements.txt /tmp/requirements.txt
COPY wait-for-it.sh /usr/bin/wait-for-it.sh
RUN bash /tmp/setup.sh


CMD ["/usr/local/bin/python3"]