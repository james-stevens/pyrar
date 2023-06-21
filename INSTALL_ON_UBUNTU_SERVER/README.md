# Installing PyRar to Run on Ubuntu Server

The plan here is to run the docker runtime & MairaDB at the operating system 
level, then run PyRar in a docker container. Everything that PyRar needs comes in its container (Python, PowerDNS etc).

PyRar will *not* be running the SSL itself, so we will also run `nginx` at the operating system level
to shed the TLS load from PyRar.

In this exmaple I am using Ubuntu Server, but pretty much any linux will do. You'll just have to
google / adjust the commands as appropriate. I didn't chose Ubuntu Server for any particular reson,
except that its popular.  I'm using Ubuntu Server v22.04.2


# 1. Install Ubuntu Server

With Ubuntu Server, you can do either a `comfortable` or `minimal` install, I chose `comfortable`. You can probably
chose `minimal` and just install any missing packages later. But these instructions will assume
you installed `comfortable`.


# 2. Install docker

Instal docker [using these instructions](https://docs.docker.com/engine/install/ubuntu/)

As per those instructions, ensure the command `docker run hello-world` displays `Hello from Docker!`



# 3. Install Mariadb

Follow Steps 1 & 2 from [here](https://www.digitalocean.com/community/tutorials/how-to-install-mariadb-on-ubuntu-20-04)

When you run `mysql_secure_installation`, answer `Y` to everything and set a password for the MariaDB `root` user.


At about line 27 of `/etc/mysql/mariadb.conf.d/50-server.cnf` change

	bind-address            = 127.0.0.1

to read

	bind-address            = 0.0.0.0

then restart Mariadb with `sudo systemctl restart mariadb`



# 4. Pull the PyRar Git Repo - It contains some install scripts

All these commands should be run as `root`, either by logging in as `root` or using the `sudo` prefix.

	$ sudo cd /opt
	$ sudo git clone https://github.com/james-stevens/pyrar.git


# 5. Now the rest

Install some other things and copy a base config

	$ sudo apt install jq net-tools nginx
	$ sudo cd pyrar/INSTALL_ON_UBUNTU_SERVER
	$ sudo cp -a your-config /opt/config
	$ sudo ./make_payment > /opt/config/payment.json

Edit the file `base.sql` to give unique passwords to the database users `pdns`, `reg`, `webui` and `engine`.

NOTE: `reg` is the pyrar admin user

Make the databases, add users & apply table permission

	$ sudo mysql -u root < base.sql
	$ sudo mysql -u root pdns < ../dump_schema/pdns.sql
	$ sudo mysql -u root pyrar < ../dump_schema/pyrar.sql
	$ sudo mysql -u root pyrar < grants.sql

Make some more directories & set permission

	$ sudo cd /opt
	$ sudo mkdir -m 777 storage
	$ sudo mkdir -m 700 pems
	$ sudo chmod 755 config

Get the latest copy of PyRar from `docker.com`

	$ sudo docker pull jamesstevens/pyrar

Edit the file `/etc/rsyslog.conf` at about line 16, uncomment these lines

	module(load="imudp")
	input(type="imudp" port="514")

Restart `rsyslog`

	$ sudo systemctl restart rsyslog

This will allow the pyrar container to syslog to the Ubuntu syslog service. By default the logging
will go into `/var/log/syslog`, but you can change that if you wish.


# 6. Setting Up Your PyRar Config

Now run `cd /opt/config` and edit the config files to suit you needs

## login.json

The only changes needed here are to change the passwords to match the passwords you put into `base.sql`.

## registry.json

If you only want to sell SLDs from TLDs that you own, copy `example_registry_one_local.json` to `registry.json`
and edit the prices, if you wish.

If you want to also sell from a single EPP Registry, copy `example_registry_one_epp_one_local.json` instead.


## priority.json

This is a JSON list of the TLDs you want listed first in a user's search results - it can be empty.

It's the names you want to promote the most.


## policy.json

This replaces policy choices from the defaults you will see in `/opt/pyrar/python/librar/policy.py`
The minimum ones you need to change are listed in the default `policy.json` provided.

For the option `dns_servers`, when you are still setting up, this PyRar can be your only Name Server, so just set `ns1` & `ns2` to point to this server.
You can set up a real second name server later. You can also use different host names, as you prefer.

For the time being, leave `syslog_server` set to `None`.

NOTE: Until you have a website name, an SSL certificate (e.g from letsencrypt) and 
confgured your site name in `policy.json`, you will not be able to access the site properly.


## payment.json

Remove payment methods you do not want to use. 

For the ones you do wish to use, edit the placeholder values with the ones
you have been given by the provider.

For Paypal, you will need to enable their webhook call-back. The URL will be

	https://[YOUR-WEBSITE-NAME]/pyrar/v1.0/webhook/[PAYPAL-WEBHOOK-STRING]/

Where `[PAYPAL-WEBHOOK-STRING]` is the `webhook` value in the `payment.json` file. 

NOTE: The PayPal Sandbox (test) & Live webhooks are set up separately in the PayPal developer dashboard.


# 7. Test Run

You should now be able to do a test run of PyRar, so run the script `/opt/pyrar/INSTALL_ON_UBUNTU_SERVER/test_run_pyrar`.

This should syslog everything to stdout, so you can see it.

If you see any error messages, particularly if you see any programs continuously restart, you have a configuration
problem and need to fix it.

If you do not get any looping programs, you are ready to continue, but first in `policy.json` change
`syslog_server` to `172.17.0.1`. This will syslog to the Ubuntu syslog service.

## A quick `docker` cheat sheet

`docker image ls` - show loaded containers
`docker pull jamesstevens/pyrar` - update the container image with the latest version
`docker ps` - show running containers
`docker stop <CONTAINER ID>` - stop a running container

where `<CONTAINER ID>` is one of the columns in the `docker ps` output.
