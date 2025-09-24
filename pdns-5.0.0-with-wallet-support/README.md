# How to add DNS Record type WALLET to PowerDNS Auth

In Apr-2025, a pull-request [already exists](https://github.com/PowerDNS/pdns/pull/15449)
to add support for the WALLET rr-type, as of now (Sep-2025) it is still waiting to go through QA.

But you don't have to wait, if you're a little handy on Linux.

# HowTo

## First Grab a Patch of their code

- `git clone git@github.com:renatoalencar/pdns.git`
- `git log` - this is so you can see where the three WALLET change commits started - clue, its after `350d49b4de2e0ebf8af9ec8cc6bd61d245e85523`
- `git diff 350d49b4de2e0ebf8af9ec8cc6bd61d245e85523 > /tmp/wallet-patch.diff`

Now you have the code changes, but there is some stuff you will need to remove.

## Now grab the source code

- From [here](https://www.powerdns.com/downloads) download "The most recent supported release of the PowerDNS Authoritative Server".
	I downloaded v5.0.0, as this was the latest at the time.
- Untar it
- Go into the directory tar just created and run `./configure`

Based on the configuration used in Alpine v3.22, I created [this configure](run_configure). I don't know what much of it means, I just used
the same options that has been used to build the Alpine package of PowerDNS Auth.

		./configure \
			--prefix=/usr \
			--sysconfdir=/etc/pdns \
			--mandir=/usr/share/man \
			--infodir=/usr/share/info \
			--localstatedir=/var \
			--libdir=/usr/lib/pdns \
			--with-modules="bind gmysql"  \
			--with-dynmodules="bind gmysql" \
			--enable-tools \
			--enable-unit-tests \
			--disable-static \
			--with-libcrypto=/usr \
			CC=cc \
			CFLAGS="-Os -fstack-clash-protection -Wformat -Werror=format-security -fno-plt" \
			LDFLAGS="-Wl,--as-needed,-O1,--sort-common -Wl,-z,pack-relative-relocs" \
			CXX=c++ \
			CXXFLAGS="-Os -fstack-clash-protection -Wformat -Werror=format-security -D_GLIBCXX_ASSERTIONS=1 -D_LIBCPP_ENABLE_THREAD_SAFETY_ANNOTATIONS=1 -D_LIBCPP_ENABLE_HARDENED_MODE=1 -fno-plt"

You can see how PowerDNS was configured on your platform using `pdns_server --version` - the last line was the configure command.

I only need MySQL/MariaDB support, so I trimmed the modules list from what comes with Alpine.

Now run `make` and in the `pdns` sub-directory you should have the critical binaries `pdns_control`, `pdnsutil` & `pdns_server`.

However, this is still stock PowerDNS Auth, so now we want to add WALLET support

- `patch -p1 < /tmp/wallet-patch.diff`

This will give some errors, but you can just (carefully) delete the references to the files that gave an error & run `patch` again.
For me this happened twice, giving the [wallet-patch.diff](wallet-patch.diff) file in this directory.
You can just use my `wallet-patch.diff`, if you are happy to do that.

Now you have patched in WALLET support, run `make` again.

Once the `make` has finished, you should have `pdns_control`, `pdnsutil` & `pdns_server` with rr-type WALLET support.

You can test this by running your patched `pdns_server`, then create a test zone & try to add a WALLET record using `pdnsutil`, for example

		./pdnsutil rrset add xn--f77hja.chug xn--f77hja.chug wallet 600 '"BTC" "1234"'

Then check it worked either using `dig` or `pdnsutil`

		./pdnsutil zone list xn--f77hja.chug

or

		dig @127.0.0.1 xn--f77hja.chug axfr

You may need to install `bind` or `bind-utils` to get `dig`.

## Or, Use my Binaries

If you are running PowerDNS Auth in a container based on Alpine v3.22, you can save yourself all this hassle by using
the three binaries in this directory. 

