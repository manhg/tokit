FROM debian:stretch-slim

COPY setup.sh /tmp/setup.sh
COPY requirements.txt /tmp/requirements.txt
COPY wait-for-it.sh /usr/bin/wait-for-it.sh
RUN bash /tmp/setup.sh
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

CMD ["/usr/local/bin/python3"]