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

During the install I was offered to include the docker runtime, so I selected this.

If you do not get offered to install docker, or docker is not included in your Ubuntu distribution,
you can find the [install instructions here](https://docs.docker.com/engine/install/ubuntu/)


# 3. Install Mariadb

Follow Steps 1 & 2 from [here](https://www.digitalocean.com/community/tutorials/how-to-install-mariadb-on-ubuntu-20-04)



# 4. Pull the PyRar Git Repo

All command line commands should be run as root, either by logging in as `root` or using the `sudo` prefix.

	# cd /opt
	# git clone https://github.com/james-stevens/pyrar.git
	# cd pyrar/INSTALL_ON_UBUNTU_SERVER
	# 

