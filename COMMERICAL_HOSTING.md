# Commerical Hosting for PyRar

*** This document is not yet finalised and prices/services may change before going live ***

Commercial hosting for instances of PyRar are available from https://pyrar.com/

# The principals of our hosting are
- Your TLDs
- Your Business
- Your Data
- Your Money

PyRar enables you to sell SLDs in any of your own TLDs or in any TLD you can interconnect your PyRar instance to (see below).

With a PyRar TLD/SLD sales solution, you are **NOT** required to sign over / stake **YOUR** TLDs to anybody else
and **ALL** payments for SLDs will come directly to you. What we provide is cloud hosting & technical support (SaaS), everything else is yours.

PyRar is provided as open source to give you the confidence you can continue your business no matter what happens.

If you are unhappy with the service at any time, we will provide you with all your data (mysql-dump & config files)
so you can move to a self-hosting instance on any public cloud. PyRar is a docker container, so there are many options for public cloud hosting.
If you are unsure about getting a public cloud instance set-up yourself, probably the best thing to do is just find a whizz-kid on Fiverr.

While you are using our servce, you will need to point the Name Servers of your TLD to the Name Servers of your instance
and we will provie you with the appropriate `DS` record so you can add `DNSSEC` security to your TLDs. This is required
so your clients (SLD owners) can do `DANE` (decentralised HTTPS).


# Prices

Prices are yet to be completely finalised, but are probably going to be as follows

## Instances

All prices are per month. All prices include
- A PyRar Server **and** a MySQL (MariaDB) Server
- Unmetered access - you will not receive any additional billing for bandwidth or data transfers.
- Unlimited 2nd line technical support for PyRar & DNS.
- 24x7 backend monitoring & maintenance by our support staff


| Size | Monthly Price | Spec |
| ---- | ------: | --- |
| Small | $75.00 | At least 10 threads |
| Medium | $150.00 | At least 25 threads |
| Large | $250.00 | Dedicated physical host, At least 50 threads |

All instances will come with one IPv4 DNS Server, in a geographic location of your choice, and one IPv6 DNS Server.

`10 threads` means 10 users can execute queries, e.g. searches, at the **exact** same time.
The 11th user's PC will automatically wait until the 1st user's query has finished, so all they will
see is an hour-glass for a little longer than otherwise.

10 simultaneous users is a surprisingly good amount. Its possible the number of threads can be extended - depending on what other services you want.

Note: All searches are done in batches of a handful at a time (configurable, default is 5), so users won't have an hour-glass for any significant time.



## Payment

Hosting fees are paid quarterly (in 3 month chunks) in advance, except the first payment, which must be for the first six months hosting.

There is no additional set-up fee, the first payment includes all set-up costs. Getting you set-up & helping you get to know
the system & get all external accounts set up can take some time, this is why we ask for the first 6 months hosting fees in advance.

Payment can be made by Bank Transfer (US, EU, UK & some others), PayPal, Bitcoin or Etherium.


## Optional Add-Ons

| Optional Add-On | Price|
| -- | -- |
| Failover Server | 50% of the price of your instance - a second PyRar Server, pointing to the same database, for fail-over/load-balancing |
| Additional DNS Server(s) | $25 per server, any geographic location of your choice, you can add as many as you want |
| Off-Shore Presence | $50 - your instance will only be accessible from an off-shore jurisdiction, e.g Seychelles, Morocco, Iceland |

* Failover Server - If you opt to have a fail-over PyRar Server, we will automatically do load-balancing & fail-over between your two servers - a fail-over server will automatically give you nearly double the performance, but will not extend the perofmance of your database
* Additional DNS Servers will improve the DNS performance of your TLDs in the geographic location they are hosted
* Off-Shore instances can include a locally registered domain name. We currently have hosting partners in the location
specified, if you require a different location, please ask.

If you wish to run your own Additional DNS Servers that's not a problem, we just need you to give us the IP Addresses so we
can configure the data transfer permissions.


# You Getting Paid

All payments for SLD will be made to you directly. We will help you set up the appropriate accounts. Currently PyRar will only support PayPal
but we will shortly support Stripe and crypto, via Coinbase.

After the payment provider deducts their fees, you will receive 100% of the remaining payment from your customer.

PyRar supports a shopping cart to help reduce your transactions costs. It also supports customers holding credit in their
account to reduce gas fees for crypto payments.


# Support

You will be expected to do the first line support. This means you have the direct correspondence with your customers.
We will support you to support your customers. 

Many customer enquiries are about payments, so only you will be able to answer those. We will have **NO** access to your payment accounts (e.g. PayPal),
unless you decide otherwise - it's your money.


# Interconnect

Phase-2 of PyRar will be to add the ability to inter-connect between separate PyRar Systems (either hosted with us or self-hosted), so that
TLDs owners can form alliances with each other & sell SLDs in each other's TLDs.

PyRar also already supports the industry standard registry protocol `EPP`, which means a PyRar instance should be able to 
also resell names from any exernal registry that supports `EPP`. This has been qualified against my `EPP` Server, but
has not yet been qualified against any third party `EPP` service.

PyRar also supports (Python) plugins on the back-end so it can talk to any registry system, including talking directly to a blockchain/crypto-ledger/dSLD 
registry, but this requires a plugin to be written for that system.

