# Installing PyRar to Run on Ubuntu Server

The plan here is to run docker runtime & MairaDB a the operating system 
level, then run PyRar in a docker container. Everything that PyRar needs comes in its container (Python, PowerDNS etc).

PyRar will *not* be running the SSL itself, so we will also run `nginx` at the operating system level
to shed the TLS load from PyRar.

In this exmaple I am using Ubuntu Server, but pretty much any linux will do. You'll just have to
google / adjust the commands as appropriate. I didn't shose Ubuntu Server for any particular reson
except that its popular.

I'm using Ubuntu Server v22.04.2


# 1. Install Ubuntu Server

You can do either a "comfortable" or "minimal" install. I chose "comfortable". You can probably
chose "minimal" and just install any missing packages later. But these instructions will assume
you installed "comfortable".


# 2. Install docker

Instal docker [using the instructions here](https://docs.docker.com/engine/install/ubuntu/)

As per those instructions, ensure the command `docker run hello-world` displays `Hello from Docker!`



# 3. Install Mariadb

Follow Steps 1 & 2 from [here](https://www.digitalocean.com/community/tutorials/how-to-install-mariadb-on-ubuntu-20-04)

When you run `mysql_secure_installation`, answer `Y` to everything and set a password for the MariaDB `root` user.



# 4. Pull the PyRar Git Repo

All command line commands should be run as root, either by logging in as `root` or using the `sudo` prefix.

	$ sudo cd /opt
	$ sudo git clone https://github.com/james-stevens/pyrar.git


# 5. Now the rest

Install some other things and copy a base config

	$ sudo apt install jq net-tools nginx
	$ sudo cd pyrar/INSTALL_ON_UBUNTU_SERVER
	$ sudo cp -a your-config /opt/config

Edit the file `base.sql` to give unique passwords to the database users `reg`, `webui` and `engine`.

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
	$ sudo chmod 700 config

Get the latest PyRar

	$ sudo docker pull jamesstevens/pyrar

Edit the file `/etc/rsyslog.conf` and uncomment these lines

	module(load="imudp")
	input(type="imudp" port="514")

Restart `rsyslog`

	$ sudo systemctl restart rsyslog

This will allow the pyrar container to syslog to the Ubuntu syslog service. By default its logging
will go into `/var/log/syslog`, but you can change that if you wish.
