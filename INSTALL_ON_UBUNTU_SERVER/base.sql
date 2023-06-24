create database pyrar;
create database pdns;
create user webui identified by "[WEBUI-USER-PASSWORD]";
create user engine identified by "[ENGINE-USER-PASSWORD]";
grant all privileges on pyrar.* to 'reg'@'%' identified by '[PYRAR-DATABASE-ADMIN-PASSWORD]' with grant option;
grant all privileges on pdns.* to 'pdns'@'%' identified by '[PDNS-DATABASE-PASSWORD]' with grant option;
