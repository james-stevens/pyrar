grant select,insert,update,delete on actions to webui,raradm,engine
grant insert,select on backend to webui
grant select,insert,update,delete on backend to engine
grant insert,update,select on contacts to raradm,engine,webui
grant select,insert,update,delete on deleted_domains to engine
grant select,insert,update,delete on domains to engine,webui
grant insert,select on events to webui,engine
grant select,insert,update,delete on orders to engine,webui
grant select, insert, update, delete on payments to webui,engine
grant insert,update,select on sales to webui
grant select,insert,update,delete on sales to engine
grant select, insert, update, delete on session_keys to webui,engine
grant select, update, insert on transactions to webui,engine
grant select, insert, update on users to webui
grant select, update, delete on users to engine
grant select,insert,update on zones to engine,webui
