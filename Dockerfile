# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements are possible, contact me for more information

FROM alpine:3.16

RUN rmdir /run
RUN ln -s /dev/shm /run
RUN apk add nginx curl

RUN apk add python3 py3-flask py3-gunicorn jq py-pip py3-xmltodict py3-tz tzdata
RUN pip install apscheduler httpx

RUN apk add sysklogd
RUN rm -f /etc/syslogd.conf; ln -s /run/syslogd.conf /etc/syslogd.conf

RUN rm -rf /tmp
RUN rmdir /var/lib/nginx/tmp /var/log/nginx 
RUN ln -s /dev/shm /tmp
RUN ln -s /dev/shm /var/lib/nginx/tmp
RUN ln -s /dev/shm /var/log/nginx
RUN ln -s /dev/shm /run/nginx
RUN ln -fns /run/nginx.conf /etc/nginx/nginx.conf
RUN ln -fns /run/inittab /etc/inittab

RUN mkdir -m 755 -p /opt/pyrar /opt/pyrar/etc /opt/pyrar/pems
COPY pems /opt/pyrar/pems/

RUN mv /opt/pyrar/pems/myCA.pem /opt/pyrar/pems/myCA-2.pem /etc/ssl/private/
RUN cd /etc/ssl/private; cat myCA.pem myCA-2.pem >> /etc/ssl/cert.pem

COPY python /opt/pyrar/python/
RUN python3 -m compileall /opt/pyrar/python/

RUN ln -fns /opt/pyrar/python/bin/pysqlsh /usr/bin/sqlsh
RUN ln -fns /opt/pyrar/python/bin/flat.py /usr/bin/flat

COPY bin /usr/local/bin/
COPY htdocs /opt/pyrar/htdocs/

CMD [ "/usr/local/bin/run_init" ]
