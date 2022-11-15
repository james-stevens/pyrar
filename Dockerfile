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

RUN mkdir -m 755 -p /usr/local/pyrar /usr/local/pyrar/etc /usr/local/pyrar/pems
COPY pems /usr/local/pyrar/pems/
COPY htdocs /usr/local/pyrar/htdocs/

RUN mv /usr/local/pyrar/pems/myCA.pem /usr/local/pyrar/pems/myCA-2.pem /etc/ssl/private/
RUN cd /etc/ssl/private; cat myCA.pem myCA-2.pem >> /etc/ssl/cert.pem

COPY python /usr/local/pyrar/python/
RUN python3 -m compileall /usr/local/pyrar/python/

RUN ln -fns /usr/local/pyrar/python/pysqlsh /usr/bin/sqlsh
RUN ln -fns /usr/local/pyrar/python/flat.py /usr/bin/flat

COPY bin /usr/local/bin/

CMD [ "/usr/local/bin/run_init" ]
