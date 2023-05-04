grant insert,select on backend to webui
grant insert,select on events to webui,engine
grant insert,update,select on contacts to engine,webui
grant insert,update,select on sales to webui
grant select on class_by_name to engine,webui
grant select on class_by_regexp to engine,webui
grant select, insert, update on users to webui
grant select, insert, update, delete on payments to webui,engine
grant select, insert, update, delete on session_keys to webui,engine
grant select, update, delete on users to engine
grant select, update, insert on transactions to webui,engine
grant select, update, insert, delete on messages to webui,engine
grant select,insert,update on zones to engine,webui
grant select,insert,update,delete on actions to webui,engine
grant select,insert,update,delete on backend to engine
grant select,insert,update,delete on deleted_domains to engine
grant select,insert,update,delete on domains to engine,webui
grant select,insert,update,delete on orders to engine,webui
grant select,insert,update,delete on sales to engine
