create database pyrar;
create database pdns;
create user reg identified by "[REG-PASSWORD]";
create user webui identified by "[WEBUI-PASSWORD]";
create user engine identified by "[ENGINE-PASSWORD]";
grant all privileges on pyrar.* to 'reg'@'%' identified by '[REG-PASSWORD]' with grant option;
