# Installing PyRar to Run on Ubuntu Server

The plan here is to run the docker runtime & MariaDB at the operating system 
level, then run PyRar in a docker container. Everything that PyRar needs comes in its container (Python, PowerDNS etc).

PyRar will only be accessible to `localhost`, so we will run `nginx` to provide SSL services & give
the outside world access to PyRar & its admin system. This improves security.

`nginx` may not be necessary if you are using a hosting service that will so the SSL for you - AWS can do this.

In this example I am using Ubuntu Server, but pretty much any linux should work. You'll just have to
google / adjust the commands as appropriate. I didn't chose Ubuntu Server for any particular reason,
except that its popular.  I'm using Ubuntu Server v22.04.2


## Using a hosting provider

You can use a hosting provider to host the database, provide the SSL service or even run the container native. 

If you are doing all or any of these, the instruction below should be helpful, but will not work
out-of-the-box. Each hosting provider is different, so it is impossible for me to provide instructions
for them all.

If you use a hosting provider to run the container directly, it will need three permanent storage areas
mapped to these directories inside the container

	/opt/pyrar/storage
	/opt/pyrar/config
	/opt/pyrar/pems

<table>
<tr><td><code>storage</code></td><td>long term disk storage for PyRar, e.g. email spooling etc, you can provide this empty.</td></tr>
<tr><td><code>config</code></td><td>contains your config files (see below)</td></tr>
<tr><td><code>pems</code></td><td>contains the client side certificates required for EPP. Not required if you don't sell names from an external EPP registry.</td></tr>
</table>


# The Actual Install

## 1. Install Ubuntu Server

With Ubuntu Server, you can do either a `comfortable` or `minimal` install, I chose `comfortable`. You can probably
chose `minimal` and just install any missing packages later. But these instructions will assume
you installed `comfortable`.

Then make sure you're up-to-date

	sudo apt update
	sudo apt upgrade


## 2. Install docker

Install docker [using these instructions](https://docs.docker.com/engine/install/ubuntu/)

As per those instructions, ensure the command `docker run hello-world` displays `Hello from Docker!`


## 3. Install MariaDB

	sudo apt install mariadb-server
	sudo systemctl start mariadb.service
	sudo mysql_secure_installation

Copied [from here](https://www.digitalocean.com/community/tutorials/how-to-install-mariadb-on-ubuntu-20-04).

When you run `mysql_secure_installation`, answer `Y` (the default) to all prompts and set a password for the MariaDB `root` user.


At about line 27 of `/etc/mysql/mariadb.conf.d/50-server.cnf` change

	bind-address            = 127.0.0.1

to read

	bind-address            = 172.17.0.1

now edit `/etc/systemd/system/multi-user.target.wants/mariadb.service`, at about line 27, change

	After=network.target

to

	After=network.target docker.service

NOTE: If you ever upgrade MariaDB, its possible you will get warnings about the fact you have changed a file that came with
the package, but we really need `docker` to start before MariaDB, so the IP Address `172.17.0.1` is set-up.

then run

	 sudo systemctl daemon-reload
	 sudo systemctl restart mariadb

`172.17.0.1` is the docker "loop-back" address, so allows programs in containers to talk to services running in the host operating
system, without exposing your service to the entire globe!

I would also recommend you enable the [query cache in MariaDB](https://mariadb.com/kb/en/query-cache/). A TL;DR about
[how to do that is here](https://ivan.reallusiondesign.com/enabling-query-cache-for-mariadb-mysql/),
more info at Google ;)


## 4. Pull the PyRar Git Repo - It contains some install scripts

All these commands should be run as `root`, either by logging in as `root` or using the `sudo` prefix.

	cd /opt
	sudo git clone https://github.com/james-stevens/pyrar.git


## 5. Now the rest

Install some other things and copy a base config

	sudo apt install jq net-tools nginx
	cd /opt/pyrar/INSTALL_ON_UBUNTU_SERVER
	sudo cp -a default-config /opt/config
	sudo ./make_payment > /opt/config/payment.json

Edit the file `base.sql` to give unique passwords to the database users `pdns`, `reg`, `webui` and `engine`.
NOTE: `reg` is the pyrar admin user

You can run the program `/opt/pyrar/INSTALL_ON_UBUNTU_SERVER/random_password` to generate passwords
that should be sufficiently secure.


Make the databases, add users & apply table permission

	sudo mysql -u root < base.sql
	sudo mysql -u root pdns < ../dump_schema/pdns.sql
	sudo mysql -u root pyrar < ../dump_schema/pyrar.sql
	sudo mysql -u root pyrar < grants.sql

Make some more directories & set permission

	cd /opt
	sudo mkdir -m 777 storage
	sudo mkdir -m 755 pems
	sudo chmod 755 config

Get the latest copy of PyRar from `docker.com`

	sudo docker pull jamesstevens/pyrar

Edit the file `/etc/rsyslog.conf` at about line 16, uncomment these lines

	module(load="imudp")
	input(type="imudp" port="514")

Restart `rsyslog`

	sudo systemctl restart rsyslog

This will allow the pyrar container to syslog to the Ubuntu syslog service. By default the logging
will go into `/var/log/syslog`, but you can change that if you wish.




## 6. Setting Up Your PyRar Config

Now run `cd /opt/config` and edit the config files to suit your needs

### `logins.json`

The only changes needed here are to change the passwords to match the passwords you put into `base.sql`.

### `registry.json`

If you only want to sell SLDs from TLDs that you own, copy `example_registry_one_local.json` to `registry.json`
and edit the prices, if you wish.

If you want to also sell from a single EPP Registry, copy `example_registry_one_epp_one_local.json` instead.


### `priority.json`

This is a JSON list of the TLDs you want listed first in a user's search results - it can be empty.

It's the names you want to promote the most.


### `policy.json`

This replaces policy choices from the defaults you will see in `/opt/pyrar/python/librar/policy.py`
The default file contains the minimum ones you need to change.

It is likely that `[YOUR-WEBSITE-NAME]` and `[YOUR-DOMAIN-NAME]` are the same, but they may not be.

For the option `dns_servers`, when you are still setting up, this PyRar can be your only Name Server, so 
(in your DNS) just set `ns1` & `ns2` to point to this server.
You can set up a real second name server later. You can also use different host names, as you prefer.

For the time being, leave `syslog_server` set to `None`.

NOTE: Until you have a website name, an SSL certificate (e.g from letsencrypt) and 
configured your site name in `policy.json`, you will not be able to access the site properly.


### `payment.json`

Remove payment methods you do not want to use. 

For the ones you do wish to use, edit the placeholder values with the ones
you have been given by the provider.

For Paypal, you will need to enable their webhook call-back. The URL will be

	https://[YOUR-WEBSITE-NAME]/pyrar/v1.0/webhook/[PAYPAL-WEBHOOK-STRING]/

Where `[PAYPAL-WEBHOOK-STRING]` is the `webhook` value in the `payment.json` file. 

NOTE: The PayPal Sandbox (test) & Live webhooks are set up separately in the PayPal developer dashboard.

[NowPayments](https://nowpayments.io/) does not require a pre-configured callback webhook URL. Using the API-Key,
PyRar passes a single use webhook URL when requesting payment.
However, NowPayments does require that you enable webhook callbacks in your account settings. By default
they are disabled. If you do not enable them, your request to be called-back will be silently ignored,
i.e. user accounts will not get automatically credited after they have paid.


### Checking your JSON

Now check your JSON is valid using `jq`, you shouldn't need a `sudo` prefix.

	jq -c < /opt/config/logins.json
	jq -c < /opt/config/payment.json
	jq -c < /opt/config/policy.json
	jq -c < /opt/config/priority.json
	jq -c < /opt/config/registry.json

If these succeed, then you will get your JSON displayed, if they fail `jq` will tell you the line
with the error. Remove the `-c` for a prettier, but longer, output.


## 7. Test Run

You should now be able to do a test run of PyRar, by running the script `/opt/pyrar/INSTALL_ON_UBUNTU_SERVER/run_pyrar`.
This should log everything to your terminal session, so you can see it.
If you see any error messages, particularly if you see any programs continuously restart, you have a configuration
problem and need to fix it.

If you do not get any looping programs, you are ready to continue, but first in `policy.json` change
`syslog_server` to `172.17.0.1`. This will syslog PyRar services to the Ubuntu syslog server.
Usually this will log PyRar logs into `/var/log/syslog`.

### A quick `docker` cheat sheet

<table>
<tr><th> Command</th><th>What it does</th>
<tr><td nowrap><code>docker image ls</code></td><td>show containers you have downloaded</td></tr>
<tr><td nowrap><code>docker pull jamesstevens/pyrar</code></td><td>update the container image with the latest version</td></tr>
<tr><td nowrap><code>docker ps</code></td><td>show running containers</td></tr>
<tr><td nowrap><code>docker stop <CONTAINER ID></code></td><td>clean shutdown a running container, where <code>CONTAINER ID</code> is the first column in the <code>docker ps</code> output.</td></tr>
<tr><td nowrap><code>docker exec -it <CONTAINER ID> /bin/sh</code></td><td>shell into a container</td></tr>
</table>


## 8. Testing the Test-Run

	$ dig @127.0.0.1 tlds.pyrar.localhost

This should return an `SOA` record for the zone `tlds.pyrar.localhost`, including this

	;; AUTHORITY SECTION:
	tlds.pyrar.localhost.   3600    IN      SOA     ns1.exmaple.com. hostmaster.tlds.pyrar.localhost. 1687436967 10800 3600 604800 3600

If this works, but returns no `SOA` record, you probably didn't set the `dns_servers` value correctly.

Now run:

	$ curl http://127.0.0.1:800/pyrar/v1.0/config

this should return `{"error":"Website continuity error"}`


## 9. Adding External Access

**IF** you are using a hosting service that will do the SSL for you in their infrastructure, then you 
do not want to be running `nginx`. Some AWS services include running SSL for you.

if this is the case for you, run the following

	sudo systemctl stop nginx
	sudo systemctl remove nginx
	sudo cp opt/pyrar/INSTALL_ON_UBUNTU_SERVER/run_pyrar.without_nginx /usr/local/bin/run_pyrar

This will run the user website to port 80 (HTTP) and run the admin web/ui on port 1000, so you will 
need to configure your hosting provider to direct the traffic to these ports.

Otherwise, now we'll get the `nginx` server running to provide SSL access to the PyRar container.

First you need to upload your SSL PEM, that includes both the CA Ceritficate & the private key, to `/etc/nginx/certkey.pem`

If you have a LetsEncrypt data set, go into the directory of LetsEncrypt files for the domain, then
run

	$ cat fullchain.pem privkey.pem > certkey.pem

and upload `certkey.pem` to `/etc/nginx`.

NOTE: The config provided assumes that the one certificate is for both your domain & your domain with a wildcard prefix, 
e.g. `example.com` and `*.example.com`. This is not necessary, but makes life easier. If your certificate is different
you will need to edit the `nginx.conf` provided.

	cd /opt/pyrar/INSTALL_ON_UBUNTU_SERVER
	sudo mv /etc/nginx/nginx.conf /etc/nginx/nginx.conf.orig
	sudo cp nginx.conf /etc/nginx/

Now edit `/etc/nginx/nginx.conf` and change the placeholder to your domain name, then run `nginx -t` to check the config is valid, 
if it passes, restart `nginx`, with

	sudo systemctl restart nginx

NOTE: there are two website names in the `nginx.conf`, one for users to reach the normal site and one for sysadmins
to reach the admin interface.


## 10. Loading the site

Assuming you have the same website name in `policy.json` and `nginx.conf` and you have the DNS set up to point to this server,
you should now be able to load both the user's site and the admin site in a browser.

Until you create any sysadmin logins, the default login of `pyrar` & password `pyrar` should work.

When you click the `PowerDNS` button (top right of the admin site), you will be taken into a generic PowerDNS Admin UI. 
As you are already logged in, you do not need the PowerDNS API-Key, so just click `Load Zone List` and you should see the
two zones `tlds.pyrar.localhost` and `clients.pyrar.localhost`. These are for internal use.


## 11. Running PyRar under Systemd

- From another terminal, use `docker stop <ID>` to shutdown the PyRar container you are running from the command line
- Edit `/opt/config/policy.json` and set `syslog_server` to `172.17.0.1`

Now

	cd /opt/pyrar/INSTALL_ON_UBUNTU_SERVER
	sudo cp run_pyrar stop_pyrar /usr/local/bin
	sudo cp pyrar.service /etc/systemd/system
	sudo systemctl daemon-reload
	sudo systemctl enable pyrar
	sudo systemctl start pyrar

You should now have PyRar runnning in the background as a service. You can check that by running

	sudo systemctl status pyrar

Don't worry about a `postfix/readme` message.

If PyRar is running, then you should be able to get to the PyRar websites again now. You can also
stop & restart PyRar in the normal way using `systemctl`.

PyRar should also automatically start at boot time, once `docker`, `mariadb` and `nginx` have started, so you might
want to reboot your server just to check that.

If the container crashes, `systemd` should restart it, but if you cleanly shut down the container using `docker` or `systemctl` it
will stay down, until you use `systemctl start pyrar` to start it again.


IMPORTANT: Before going any further, it is STRONGLY recommended that you create one or more sysadmin users in the admin web/ui.


## 12. Add your TLDs

You now need to add to the system all the domains you will be selling sub-domains from.

Go into the Admin Web/UI, click the `Add to Table` drop down and select `zones` and you'll get a form.

The only items that you really MUST fill out are `Zone` which is the name of the zone and `Price Info`, which is a JSON
of the prices you wish to charge for names in the zone.

If this is your zone you are selling names in then, the `Registry` is `local`. For EPP zones, see below.

For prices, the minimum JSON is

	{
	"create": 10.00,
	"renew": 10.00
	}

This sets the new & renew prices to $10.00 for names in this zone.

You can change currency by setting a different currency in the `policy.json` file, but you really MUST do this right at the beginning.

As soon as you add a zone, the system will pick it up, but users won't see it until they reload, or close & reopen the site.

Once users have reloaded the site, when they do a search the newly added zone should now come up.


# You're done

Essentially, the install in now done - its just for you to complete setting it up how you want it.


# Setting Up The DNS in Your Domain

If you have followed this installation, you will need four IP Address entries in your domain.
They are for the hosts `@`, `admin`, `ns1` and `ns2` - where `@` means the zone itself.
For example, if your PyRar server's external IP Address is `64.65.66.67`, then you would add the following
into your domain's DNS - this is usually done at your registrar, where you bought the domain.

	@     IN  A  64.65.66.67
	ns1   IN  A  64.65.66.67
	ns2   IN  A  64.65.66.67
	admin IN  A  64.65.66.67

These records will also need a `TTL`, this depends on how often you think you might change these
values. If you are not sure, `3600` is probably a reasonable choice to start with.

You do not have to use the name `admin` for the Admin/UI, but whatever name you choose must be matched in the `nginx.conf`
and you must have a valid certificate for it. If you have a wildcard certificate (as recommended), then
you are free to choose any name you wish.

Documentation for setting up addititonal and/or external Name Servers will follow in due time.


# Security & Firewalls

The only ports you need exposed to the outside world are

| Port | Meaning |
| ---- | ------- |
| TCP/443 | HTTPS, for access to the web/ui & admin/ui |
| TCP/53 | DNS |
| UDP/53 | DNS |
| TCP/22 | SSH - preferably restricted, not just open to the world |

If you are not using an external firewall, it is recommended you [set up the firewall](https://www.digitalocean.com/community/tutorials/how-to-set-up-a-firewall-with-ufw-on-ubuntu-22-04)
in Ubuntu Server.

If you have enough bandwidth, and low enough latency, on your home internet connection, you can run PyRar on a PC server at home.
[My demo site](https://nameshake.net) runs on my home DSL line which has 75Mb/s down & 25Mb/s up and less than 8ms `ping` response
to the main UK/IX.

If you google "internet speed test" and run the Google test provided, it will show you these three stats for your connection.

Most home DSL routers support "port forwarding", so configure your router to forward the HTTPS & DNS ports (shown above) to your PyRar Server.
With only these ports forwarded, your server should be reasonbly secure, assuming the other machines on your network don't get attacked!!

NOTE: Exposing port 3306 (MariaDB) to the entire world is **HIGHLY* undesirable.



# Twin Server Install

If you wish you can install the database server & docker runtime server (PyRar Server) as two separate linux systems.
Just run the MariaDB install on a DB server, instead of the docker server, then run all the `mysql -u root` commands on
the DB server.

This will require that you copy a few `.sql` scripts from the PyRar Server to the DB Server.

You will then have to change the IP Address in `logins.json` from `172.17.0.1` to the IP Address
of your DB Server.


# Notes on DB Logins

The DB identities `admin`, `webui` and `engine` (in `logins.json`) are roles, not fixed user names.
For security, I have not used `admin` as the admin user cos this is too easy to guess, but have used `reg`
instead. For `webui` and `engine` I have used the role name as the login name, to simplify the configuration.

Where the role & login name are different, you must specify the role's value as an array of two items `[usernane,password]`, but
where the role & login name are the same, you only need to specify the password as a string. For exmaple

	"webui": "some-webui-password",

... or ...

	"admin": [ "reg", "the-admin-password" ],

If you are using an external database service, like AWS, you may not be able to control what user names you
are allowed to use, so just specify both the username & password for each role.

When using an external database service, you will also need to edit the `base.sql` & `grants.sql` scripts.


# Connecting to EPP Registries

To connect to an external EPP registry, you need to set up the registry in `registry.json` and set up its login in `logins.json`.

Each EPP registry will have a name of your choice, say "example". The `logins.json` will have three properties, `username`, `password` and `server`.
So the `logins.json` entry for `example` might look like this

	"example" : {
		"username": "my-login",
		"password": "my-password",
		"server": "epp.example.com"
		}

The `registry.json` entry must have `desc`, `type` (which is `epp`), `sessions` and `prices`.

<table>
<tr><td><code>desc</code></td><td>A text string of your choice</td></tr>
<tr><td><code>type</code></td><td>For EPP registries this is <code>epp</code></td></tr>
<tr><td><code>sessions</code></td><td>Number of simultaneous EPP sessions the registry will allow you / you want to maintain</td></tr>
<tr><td><code>prices</code></td><td>A JSON of the prices you wish to charge. This can specify a fixed price, a multiplication factor or a fixed addition to the registry price</td></tr>
</table>

For exmaple

	"example": {
		"desc": "An exmaple EPP registry",
		"type": "epp",
		"sessions": 3,
		"prices" : { "default": "x1.5" }
		}

In this example, we are going to charge our users a 50% mark up of the whole sale price of the domains.

EPP requires that you present a client-side certificate. Different registries have different requirements on this,
so you will need to find out from them what they require. Some will issue you with your client-side certificate.

Once you have a client side certificate you must copy it into `/opt/pems` with the name of the service and the suffix `.pem`.
In our example that would be `/opt/pems/example.pem`.

Most changes to the `config` file will happen immediately, but to add or remove an EPP service, you must restart the PyRar container with

	sudo systemctl restart pyrar
