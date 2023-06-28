export EXTERNAL_IP_ADDRESS="[YOUR-EXTERNAL-IP]"

if test "${EXTERNAL_IP_ADDRESS}" = "[YOUR-EXTERNAL-IP]"
	then
		echo ""
		echo "ERROR: You need to edit '/usr/local/etc/external_ip.inc' and set your server's external IP Address"
		echo ""
		exit 1
	fi
