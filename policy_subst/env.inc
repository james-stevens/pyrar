export LOGLEVEL_PYTHON="{{policy.logging_python_level}}"
export FACILITY_PYTHON="{{policy.logging_python}}"

export LOGLEVEL_NGINX="{{policy.logging_nginx_level}}"
export FACILITY_NGINX="{{policy.logging_nginx}}"

if test "{{policy.syslog_server}}" -a ! "{{policy.syslog_server}}" = "None"
	then
		export SYSLOG_SERVER="{{policy.syslog_server}}"
	fi

export WEBUI_SESSIONS="{{policy.webui_sessions}}"
export ADMIN_SESSIONS="{{policy.admin_sessions}}"

