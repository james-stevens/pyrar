# Open Source EPP DNS Registrar & simple self-contained Registry
Python engine & rest/api with JS webui to provide a complete Domain Name Registrar

### This software is still undergoing constant & rapid development, so please come back later

To see a demo of it running the current latest `master` go to https://nameshake.net/

A lot works, but there's also a lot more to do.

If you want to play with buying domains on the demo, I can give you some fake credit, just ask.


# Help with this effort

If you would like to help with this development effort, right now, the absolutely biggest help
would be to help fund it.

- [Donate by PayPal](https://www.paypal.com/donate/?hosted_button_id=L8ABXW4X8W6BW)
- Donate by BTC - 357ynBdTQiVKybo93bP2cYbrkLbpGmQCj6
- Donate by ETH - 0x20fbf9555F09a8579540970488dcB8245244b683 (Etherium Network ONLY)

Donations are paid into a UK Limited Company, so if you want a trade invoice / recipt, just ask.

Or you can sponsor me [through GitHub](https://github.com/sponsors/james-stevens) - Also see `Sponsor this project`


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


## A Basic Registry

PyRar can also run as a basic self-contained registry platform. It does **not** support
in-bound EPP connections (e.g. from other registrars) or differential pricing, but
if you own a TLD, and all you want to do is sell names yourself at a flat price, PyRar will do the job.

It maintains the TLD in PowerDNS, adding & removing SLDs as they are bought / expire. By default
TLDs are signed `NSEC3+OptOut KSK+ZSK ECDSA256`. This can be reconfigured, or you can pre-create
the TLD with the DNSSEC options of your choice.

## Plug-Ins

Different back-ends, to sell domains from, are supported using plug-ins. These are python code files
that register a series of call-backs for the functions that are required, e.g. get-price, buy-domain, renew-domain, etc

Currently the only plug-ins provided are `epp` and `local`, but it should be possible to write plug-ins for
domain registry systems that follow the same basic model. Support for auction based sale systems would require significant code changes.

This means it should be relatively easy to write a plug-in for a block-chain based domain name system, if it supports fixed price domains.

The EPP plug-in has only been tested with a registry that supports the [RFC 8748](https://www.rfc-editor.org/rfc/rfc8748) `fee-1.0` extension,
but registries that do not support this should work, although setting up the pricing will be more work!

Registries that use differential prices, but do not support `fee-1.0` would not be supported without significant code changes.

By "differential prices", I mean different prices for different domains (e.g. most newGTLDs), as opposed to a single flat price (e.g. COM & NET).


#  What Works - right now

## Users / Accounts
- Register
- Login
- Logout
- View & edit details
- Run an account
- View a history of transactions
- Change password
- Password reset
- Maintain payment options e.g. card / account details etc (some done, still needs work)
- Close account

## Domains
- Search for available domains
- Buy domains
- Renew domains
- Auto-Renew domains (partly working)
- Gift a domain to a user on the same platform
- Transfer domains using the standard AuthCode mechanism
- Edit NS and DS records
- Edit a locally hosted client zone file
- Sign / Unsign locally hosted client zone file
- Offer domains for sale to others users (partly working)
- Event log to give a history of the domain (for admin)

# Engine
- All function required to support an EPP registry (delayed transfers needs work)
- All functions required to support running a simple registry locally
- Create and process jobs for aging domains (renewal reminders, auto-renew, expire, delete)
- Cronjob for routine maintenance
- Background processing payments after credit comes in

## Admin Web/UI
- A Web/UI to the PowerDNS server is provided
- find a user's account
- find a domain
- cross-links between related table data
	- view domain history
	- view transaction history
	- view activity history

## EMails
- Can email users from template, either plain text or HTML
- Password Reset request
- Password reset confirmation
- Renewal Reminder
- Verify User's email address



# What doesn't work, yet

It's getting pretty close to ready to use !


## Users
- 2fA (enable & disable)
- Make payments - e.g. PayPal, Stripe, Coinbase

## Domains
- UI to request transfers (some done)
- Auto-renewals
- Ability to "recover" an expired domain


## EPP
- Poll for messages and know what some mean!!


## Admin Web/UI
A web/ui for standard / usual admin tasks is planned, for example
- refunds
- check data held at registry (in EPP)
- add & remove users for the admin system

