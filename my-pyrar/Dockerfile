FROM jamesstevens/pyrar

# remove the default/test config files
RUN rm -f /opt/pyrar/etc/*
RUN rm -f /opt/pyrar/pems/*

# install my config
COPY pems /opt/pyrar/pems/
COPY config /opt/pyrar/config/
