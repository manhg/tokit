FROM debian:stretch-slim

COPY setup.sh /tmp/setup.sh
COPY reqs.txt /tmp/reqs.txt
COPY reqs.txt /tmp/reqs_build.txt
RUN bash /tmp/setup.sh
RUN pip3 install --no-cache-dir -r /tmp/reqs_build.txt
RUN pip3 install --no-cache-dir -r /tmp/reqs.txt

CMD ["/usr/local/bin/python3"]