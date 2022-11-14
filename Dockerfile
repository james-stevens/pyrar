# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements are possible, contact me for more information

FROM alpine:3.16

RUN rmdir /run
RUN ln -s /dev/shm /run
RUN apk add nginx curl

RUN apk add python3 py3-flask py3-gunicorn

RUN apk add sysklogd
RUN rm -f /etc/syslogd.conf; ln -s /run/syslogd.conf /etc/syslogd.conf

RUN apk add yq

RUN rmdir /tmp /var/lib/nginx/tmp /var/log/nginx 
RUN ln -s /dev/shm /tmp
RUN ln -s /dev/shm /var/lib/nginx/tmp
RUN ln -s /dev/shm /var/log/nginx
RUN ln -s /dev/shm /run/nginx
RUN ln -fns /run/nginx.conf /etc/nginx/nginx.conf
RUN ln -fns /run/inittab /etc/inittab

COPY pems/myCA.pem pems/myCA-2.pem /etc/ssl/private/
RUN cd /etc/ssl/private; cat myCA.pem myCA-2.pem >> /etc/ssl/cert.pem

RUN mkdir -m 755 -p /usr/local/pyrar /usr/local/pyrar/etc /usr/local/pyrar/pems
COPY pems/certkey.pem /usr/local/pyrar/pems/client.pem
COPY htdocs /usr/local/pyrar/htdocs/

COPY python /usr/local/pyrar/python/
RUN python3 -m compileall /usr/local/pyrar/python/

COPY bin /usr/local/bin/

CMD [ "/usr/local/bin/run_init" ]
