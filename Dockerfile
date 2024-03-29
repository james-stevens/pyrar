# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements are possible, contact me for more information

FROM alpine:3.16
RUN apk update
RUN apk upgrade

RUN rmdir /run
RUN ln -s /dev/shm /run
RUN mkdir /run/policy_subst
RUN apk add nginx curl
RUN addgroup nginx daemon

RUN apk add python3 jq py-pip
RUN apk add py3-flask py3-gunicorn py3-xmltodict py3-tz py3-bcrypt tzdata py3-mysqlclient
RUN apk add py3-dnspython py3-dateutil py3-jinja2 py3-yaml py3-requests py3-validators
RUN pip install apscheduler base58

RUN apk add postfix
COPY basic_start_files/aliases /etc/postfix/aliases

RUN apk add ldns-tools openssl

RUN apk add sysklogd
RUN rm -f /etc/syslogd.conf; ln -s /run/syslogd.conf /etc/syslogd.conf
RUN rm -f /etc/periodic/daily/sysklogd

RUN apk add pdns pdns-backend-mysql

RUN rm -rf /tmp
RUN rmdir /var/lib/nginx/tmp /var/log/nginx 
RUN ln -s /dev/shm /tmp
RUN ln -s /dev/shm /var/lib/nginx/tmp
RUN ln -s /dev/shm /var/log/nginx
RUN ln -s /dev/shm /run/nginx
RUN ln -fns /run/nginx.conf /etc/nginx/nginx.conf
RUN ln -fns /run/server.pem /etc/nginx/server.pem
RUN ln -fns /run/inittab /etc/inittab
RUN ln -fns /run/policy_subst/pdns.conf /etc/pdns/pdns.conf

RUN mkdir -m 755 -p /opt/pyrar /opt/pyrar/config /opt/pyrar/pems

COPY pems/myCA.pem /opt/pyrar/pems/myCA.pem
COPY pems/myCA-2.pem /opt/pyrar/pems/myCA-2.pem
RUN mv /opt/pyrar/pems/myCA.pem /opt/pyrar/pems/myCA-2.pem /etc/ssl/private/
RUN cd /etc/ssl/private; cat myCA.pem myCA-2.pem >> /etc/ssl/cert.pem

RUN ln -fns /usr/local/bin/run_actions /etc/periodic/15min/run_actions
RUN ln -fns /usr/local/bin/run_hourly_jobs /etc/periodic/hourly/run_hourly_jobs
RUN ln -fns /usr/local/bin/run_daily_jobs /etc/periodic/daily/run_daily_jobs
RUN ln -fns /usr/local/bin/check_server_pem /etc/periodic/hourly/check_server_pem

COPY emails /opt/pyrar/emails/
COPY etc /opt/pyrar/etc/
COPY policy_subst /opt/pyrar/policy_subst/
COPY bin /usr/local/bin/

COPY python /opt/pyrar/python/
RUN python3 -m compileall /opt/pyrar/python/
RUN ln -fns /opt/pyrar/python/bin/sqlsh.py /usr/bin/sqlsh
RUN ln -fns /opt/pyrar/python/bin/flat.py /usr/bin/flat

COPY admin_htdocs /opt/pyrar/admin_htdocs/
COPY htdocs /opt/pyrar/htdocs/

CMD [ "/usr/local/bin/run_init" ]
