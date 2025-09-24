# How to add DNS Record type WALLET to PowerDNS Auth

In Apr-2025, PowerDNS had already made the code change, as of now (Sep-2025)
it is still waiting to go through QA.

But you don't have to wait, if you're a little handy on Linux.

# HowTo

## First Grab a Patch of their code

- `git clone git@github.com:renatoalencar/pdns.git`
- `git log` - this is so you can see where the three WALLET change commits started - clue, its after `350d49b4de2e0ebf8af9ec8cc6bd61d245e85523`
- `git diff 350d49b4de2e0ebf8af9ec8cc6bd61d245e85523` > /tmp/wallet-patch

Now you have the code changes, but there is some stuff you will need to remove.

## Now grab the source code

- From (here)[https://www.powerdns.com/downloads] download "The most recent supported release of the PowerDNS Authoritative Server".
	I downloaded v5.0.0, as this was the latest at the time.
- Untar it
- Go into the directory tar just created and run `./configure`

Based on the configuration used in Alpine v3.22, I created this configure

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

However, this is still stock
