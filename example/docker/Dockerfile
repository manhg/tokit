FROM debian:stretch-slim

# becareful of missing files due to dockerignore
COPY ./setup.sh /tmp/setup.sh
COPY ./requirements_extra.txt /tmp/requirements_extra.txt
COPY ./requirements.txt /tmp/requirements.txt

RUN bash /tmp/setup.sh
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements_extra.txt

CMD ["/usr/local/bin/python3"]