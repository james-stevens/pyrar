# (c) Copyright 2019-2020, James Stevens ... see LICENSE for details
# Alternative license arrangements are possible, contact me for more information

FROM alpine:3.16

RUN apk update
RUN apk upgrade

RUN apk add bind

RUN mkdir -p /opt /opt/named /opt/named /opt/named/etc
RUN mkdir -p /opt/named/etc/bind /opt/named/zones /opt/named/var /opt/named/var/run

RUN cp -a /etc/bind/rndc.key /opt/named/etc/bind

RUN chown -R named: /opt/named/zones /opt/named/var
RUN rm -f /etc/periodic/monthly/dns-root-hints

COPY envsub /usr/bin/
COPY inittab /etc/inittab

COPY named.conf.pre /opt/named/etc/bind/
COPY start_bind start_syslogd /usr/local/bin/

CMD [ "/sbin/init" ]
