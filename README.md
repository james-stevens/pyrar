# Open Source EPP DNS Registrar & self-contained Registry
Python engine & rest/api with JS webui to provide a complete Domain Name Registry & Registrar

To see a demo of it running the current latest `master` go to https://nameshake.net/

It's probably now ready to go live in a limited installation - supports payment by PayPal or crypto via [NowPayments](https://nowpayments.io/)

If you want to play with buying domains on the demo, I can give you some fake credit, just ask.


# Help with this effort

If you would like to help with this development effort, right now, the absolutely biggest help
would be to help fund it.

- [Donate by PayPal](https://www.paypal.com/donate/?hosted_button_id=L8ABXW4X8W6BW)
- Donate by BTC - 357ynBdTQiVKybo93bP2cYbrkLbpGmQCj6
- Donate by ETH - 0x20fbf9555F09a8579540970488dcB8245244b683 (Etherium Network ONLY)

Donations are paid into a UK Limited Company, so if you want a trade invoice / recipt, just ask.

Or you can sponsor me [through GitHub](https://github.com/sponsors/james-stevens) - Also see `Sponsor this project`


# Fully Hosted Service

To help users go live with this system, either as a registry or registrar (or both), we plan to offer a
fully hosted & supported service that (we hope) will be price competative with public cloud.

The service will be graded by the level of performance you want, and will always be on an unmetered basis - i.e.
no surcharges for extra usage ever - the price quoted is the price you pay. Anti-D/DoS measures will be applied.

Optional extras include additonal Name Servers (e.g. in almost any part of the world, to improve DNS performance)
and the option of "off-shore" hosting at locations like Iceland, The Seychelles or Morocco.
With the option of a local "off-shore" domain name for your site.

Two Name Servers will be included in the price of all services.


## You Will
- Set up suitable payment accounts (e.g PayPal) and provide us with the API crterdentials we'd need
- All payments from users will be received by you directly
- Promote you service (PR/sales/marketing)
- Handle first level support - generally this means payment & refund issues

## We Will
- Host the PyRar Server & its required MySQL databases
- Give you full access to daily backups of the databases to download
- Provide technical back-up support
- Give you access to the Admin Web/UI for your system (but **not** command line access)


# Hosting on Public Cloud

If you would prefer, I'm sure it would not be hard to find a tech-guru on Fiverr (etc) who could
get this all set up & running for you on any public cloud of your choice. Its just a single docker container
so there are **many** places you can host it.

If you opt to host with us to begin with, but become unhappy with the service, then the daily database backups
should make it relatively simple for you to switch to public cloud at a later date.


# docker.com

A copy of the current latest `master` build as a container is available at https://hub.docker.com/r/jamesstevens/pyrar

This image is updated every time there is a merge to `master` as well as old version date-stamped.


# How PyRar works

PyRar is designed to run as a single container, with everything you need to operate a
Domain Name Registrar (reseller) included in the one container.

This includes buying & renewing domains and hosting & editing DNS for client zones (with DNS signing),
but does not include value-add services like web or email hosting for clients.

It runs as a number of micro-services within one container, so these could be split into
separate containers, but that's for the future (or for you to do).

PyRar is made of a rest/api and processing engine written in Python and a web/ui written in JS.
Replacing the JS web/ui with one of your choice should be relatively straight forward, but
it would need writing. The JS front-end provided doesn't use any specific framework.

The DNS is handled by PowerDNS, with all access done using its rest/api. This means it should
be possible to move it into a separate container without too much trouble.

A `bind` ["Catalog Zone"](https://kb.isc.org/docs/aa-01401) is automatically maintained,
so all TLD & client zones hosted can be easily slaved into any standard DNS server that supports this.

If you want to run external name servers, the PowerDNS can be configured to `NOTIFY` them
and allow zone transfers to them.


## Using PyRar as a Registry System

PyRar can also run as a self-contained registry platform. It does **not** (yet) support
in-bound EPP connections (e.g. from other registrars), but connecting between other PyRar Registry Systems
should be available shortly.

It maintains the TLD in PowerDNS, adding & removing SLDs as they are bought / expire. By default
TLDs are signed `NSEC3+OptOut KSK+ZSK ECDSA256`. This can be reconfigured, or you can pre-create
the TLD with the DNSSEC options of your choice.

If SLD owners chose to host their DNS withing the system, then their `DS` records will be automatically
updated in the TLD if they Sign/Unsign their SLD zone data. This makes running their SLD signed extremely easy.


## Plug-Ins

Different back-ends, to sell domains from, are supported using plug-ins. These are python code files
that register a series of call-backs for the functions that are required, e.g. get-price, buy-domain, renew-domain, etc

Currently the only plug-ins provided are `epp` & `local` and `PyRar` will be added shortly, but it should be possible to write plug-ins for
domain registry systems that follow the same basic model. Support for auction based sale systems would require significant code changes.

This means it should be relatively easy to write a plug-in for a block-chain based domain name system, if it supports fixed price domains.

The EPP plug-in has only been tested with a registry that supports the [RFC 8748](https://www.rfc-editor.org/rfc/rfc8748) `fee-1.0` extension,
but registries that do not support this should work, although setting up the pricing will be more work!

EPP Registries that use differential prices, will **need** to support `fee-1.0`. EPP Registries with flat pricing (all domains are the same price)
can be supprted without `fee-1.0`.


#  What Works - right now

## General
- Can automatically add tables, columns & indexes to the PyRar or P/DNS database after an upgrade


## Users / Accounts
- Register
- Login & Logout
- View & edit account details
- Run an account
- View a history of transactions
- Change password
- Password reset
- Maintain payment options e.g. card / account details etc (some done, still needs work)
- Close account
- Money Managment fully woking with push-pay via PayPal, or by crypto via NowPayment, fully working


## Domains
- Search for available domains (very fast)
	- Built-in emoji search option (super-cool feature)
- IDN & Emoji Domain fully supported
- Buy domains
- Renew domains
- Auto-Renew domains (partly working)
- Gift a domain to another user on the same platform
- Transfer domains using the standard AuthCode mechanism
- Edit NS and DS records (in the parent zone)
- Edit locally hosted client zone data
- Sign / Unsign locally hosted client zone file
- Offer domains for sale to others users (partly working)
- Support for the four EPP standard domain locks
- Automatic securing of hosts, using TLSA records & generating PEM files, for locally hosted DNS in a signed zones


# Engine
- All function required to support an EPP registry (delayed transfers needs work)
- All functions required to support running a registry locally (see below)
- Schedule and process event jobs for aging domains (renewal reminders, auto-renew, expire, delete)
- Cronjob for routine maintenance
- Background processing pending payments after credit comes in


## Admin Web/UI
- A Web/UI to the PowerDNS server is provided
- Quick search by SLD name, SLD id, user's email, user's id, TLD name
- Cross-links between related table data
	- view domain history
	- view transaction history
	- view activity history
- Search, Add, Edit, Delete rows in any table
- Add, edit, remove SysAdmins
- One click view of the P/DNS data for TLDs/SLDs
- Check domain data held at a remote EPP registry, shown in EPP format
- View event log to give a history of the domain


## EMails
- Runs a Postfix SMTP spooler with optional support for relaying out via an external mail server/service, optionally with TLS & SMTP/AUTH
- Can email users from template, either plain text or HTML
- Email Templates use the python standard `jinja2` templating package, so making your own is easy
- Supported email events are...
	- Password Reset request
	- Password reset confirmation
	- Password Changed (warning to user, just in case)
	- Renewal Reminder
	- Verify User's email address
	- Notification when you've been gifted a domain
	- Receipt for all payments
	- Domain transfer request succeeded (by EPP)
	- Payment received
	- Order processed


## Internal Registry
- Maintain the TLD zone file, automatically signed
- Support premium domain pricing
	- By individually named domain
	- By wildcard/regular expression, e.g
		- "all one/two letter SLDs" = `^(.|..)$`
		- "all unicode / punycode / emoji domain" = `^xn--`


# What doesn't work, yet

It's probably now ready to go live in a limited installation - so long as you're happy with being paid by PayPal or Crypto.


## Users
- 2fA (enable & disable)
- Make payments - Just Stripe to do
- Pull Payments for auto-renew (Stripe & PayPal only)
- Ability to opt out of emails, by type of message

## Domains
- UI to request transfers (some done)
- Auto-renewals
- Ability to "recover" an expired domain

## Contacts
Right now there is no support for contact records & attaching contact record to domains.
This may be required to be allowed to work with some EPP registries, but my preferance is for privacy!
So there is a `contacts` table, in case this functionality needs to be added, but right now its not used.

## EPP
- Poll for messages and know what some mean!!

## InterConnect
- Ability for PyRar system to connect to each other so PyRar users can resell each other's TLDs

## Admin Web/UI
- refunds (partly done)
