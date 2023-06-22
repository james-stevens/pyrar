# Installing PyRar to Run on Ubuntu Server

The plan here is to run the docker runtime & MairaDB at the operating system 
level, then run PyRar in a docker container. Everything that PyRar needs comes in its container (Python, PowerDNS etc).

PyRar will only be accessible to `localhost`, so we will run `nginx` to provide SSL services & give
the outside world access to PyRar & its admin system. This improves security.

In this exmaple I am using Ubuntu Server, but pretty much any linux should work. You'll just have to
google / adjust the commands as appropriate. I didn't chose Ubuntu Server for any particular reson,
except that its popular.  I'm using Ubuntu Server v22.04.2


# The Actual Install

## 1. Install Ubuntu Server

With Ubuntu Server, you can do either a `comfortable` or `minimal` install, I chose `comfortable`. You can probably
chose `minimal` and just install any missing packages later. But these instructions will assume
you installed `comfortable`.

Then make sure you're up-to-date

	$ sudo apt update
	$ sudo apt upgrade


## 2. Install docker

Instal docker [using these instructions](https://docs.docker.com/engine/install/ubuntu/)

As per those instructions, ensure the command `docker run hello-world` displays `Hello from Docker!`


## 3. Install Mariadb

	$ sudo apt install mariadb-server
	$ sudo systemctl start mariadb.service
	$ sudo mysql_secure_installation

Copied (from here)[https://www.digitalocean.com/community/tutorials/how-to-install-mariadb-on-ubuntu-20-04].

When you run `mysql_secure_installation`, answer `Y` (the default) to all prompts and set a password for the MariaDB `root` user.


At about line 27 of `/etc/mysql/mariadb.conf.d/50-server.cnf` change

	bind-address            = 127.0.0.1

to read

	bind-address            = 0.0.0.0

then run

	$ sudo systemctl restart mariadb



## 4. Pull the PyRar Git Repo - It contains some install scripts

All these commands should be run as `root`, either by logging in as `root` or using the `sudo` prefix.

	$ sudo cd /opt
	$ sudo git clone https://github.com/james-stevens/pyrar.git


## 5. Now the rest

Install some other things and copy a base config

	$ sudo apt install jq net-tools nginx
	$ sudo cd pyrar/INSTALL_ON_UBUNTU_SERVER
	$ sudo cp -a default-config /opt/config
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


## 6. Setting Up Your PyRar Config

Now run `cd /opt/config` and edit the config files to suit you needs

### login.json

The only changes needed here are to change the passwords to match the passwords you put into `base.sql`.

### registry.json

If you only want to sell SLDs from TLDs that you own, copy `example_registry_one_local.json` to `registry.json`
and edit the prices, if you wish.

If you want to also sell from a single EPP Registry, copy `example_registry_one_epp_one_local.json` instead.


### priority.json

This is a JSON list of the TLDs you want listed first in a user's search results - it can be empty.

It's the names you want to promote the most.


### policy.json

This replaces policy choices from the defaults you will see in `/opt/pyrar/python/librar/policy.py`
The minimum ones you need to change are listed in the default `policy.json` provided.

For the option `dns_servers`, when you are still setting up, this PyRar can be your only Name Server, so just set `ns1` & `ns2` to point to this server.
You can set up a real second name server later. You can also use different host names, as you prefer.

For the time being, leave `syslog_server` set to `None`.

NOTE: Until you have a website name, an SSL certificate (e.g from letsencrypt) and 
confgured your site name in `policy.json`, you will not be able to access the site properly.


### payment.json

Remove payment methods you do not want to use. 

For the ones you do wish to use, edit the placeholder values with the ones
you have been given by the provider.

For Paypal, you will need to enable their webhook call-back. The URL will be

	https://[YOUR-WEBSITE-NAME]/pyrar/v1.0/webhook/[PAYPAL-WEBHOOK-STRING]/

Where `[PAYPAL-WEBHOOK-STRING]` is the `webhook` value in the `payment.json` file. 

NOTE: The PayPal Sandbox (test) & Live webhooks are set up separately in the PayPal developer dashboard.

(NowPayments)[https://nowpayments.io/] does not require a pre-configured callback webhook URL. Using the API-Key,
PyRar passes a single use webhook URL when requeesting payment.


## 7. Test Run

You should now be able to do a test run of PyRar, so run the script `/opt/pyrar/INSTALL_ON_UBUNTU_SERVER/test_run_pyrar`.

This should syslog everything to stdout, so you can see it.

If you see any error messages, particularly if you see any programs continuously restart, you have a configuration
problem and need to fix it.

If you do not get any looping programs, you are ready to continue, but first in `policy.json` change
`syslog_server` to `172.17.0.1`. This will syslog to the Ubuntu syslog service.

### A quick `docker` cheat sheet

`docker image ls` - show loaded containers

`docker pull jamesstevens/pyrar` - update the container image with the latest version

`docker ps` - show running containers

`docker stop <CONTAINER ID>` - clean shutdown a running container, where `<CONTAINER ID>` is one of the columns in the `docker ps` output.


## 8. Testing the Test-Run

	$ dig @127.0.0.1 tlds.pyrar.localhost

This should return an `SOA` record for the zone `tlds.pyrar.localhost`, including this

	;; AUTHORITY SECTION:
	tlds.pyrar.localhost.   3600    IN      SOA     ns1.exmaple.com. hostmaster.tlds.pyrar.localhost. 1687436967 10800 3600 604800 3600

Now run:

	$ curl http://127.0.0.1:800/pyrar/v1.0/config

should return `{"error":"Website continuity error"}`


## 9. Adding External Access

First you need to upload your SSL PEM, that includes both the CA Ceritficate & the private key, to `/etc/nginx/certkey.pem`

If you have a LetsEncrypt data set, go into the directory of LetsEncrypt files for the domain, then
run `cat fullchain.pem privkey.pem > certkey.pem` and upload `certkey.pem` to `/etc/nginx`.

NOTE: The config provided assumes that the certificate is for both your domain & your domain with a wildcard prefix, 
e.g. `example.com` and `*.example.com`. This is not necessary, but makes life easier. If your certificate is different
you will need to edit the `nginx.conf` provided.

	$ sudo mv /etc/nginx/nginx.conf /etc/nginx/nginx.conf.orig




# Twin Server Install

If you wish you can install the database server & docker runtine server (PyRar Server) as two separate linux systems.
Just run the MaraiDB insatll on a DB server, instead of the docker server, then run all the `mysql -u root` commands on
the DB server.

This will require that you copy a few `.sql` scripts from the PyRar Server to the DB Server.

You will then have to change the IP Address in `logins.json` from `172.17.0.1` to the IP Address
of your DB Server.


# Notes on DB Logins

The DB identies `admin`, `webui` and `engine` (in `logins.json`) are roles, not fixed user names.
For security, I have not used `admin` as the admin user cos this is too easy to guess, but have used `reg`
instead. For `webui` and `engine` I have used the role name as the login name, to simplify the configuration.

Where the role & login name are different, you must specify the role's value as an array of two items `[usernane,password]`, but
where the role & login name are the same, you only need to specify the password as a string. For exmaple

	"webui": "some-webui-password",

... or ...

	"admin": [ "reg", "the-admin-passowrd" ],

If you are using an external database service, like AWS, you may not be able to control what user names you
are allowed to use, so just specify both the username & password for each role.

When using an external database service, you will also need to edit the `base.sql` & `grants.sql` scripts.
