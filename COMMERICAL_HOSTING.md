# Commerical Hosting for PyRar

*** This document is not yet finalised ***

Commercial hosting for instnces of PyRar are available from pyrar.com

# The principals of our hosting are
- Your TLDs
- Your Business
- Your Data
- Your Money

With our hosted TLD/SLD sales solution, you are **NOT** required to sign over / stake **YOUR** TLDs to anybody else
and **ALL** payments for SLDs will come directly to you. What we provide is cloud hosting & technical support, everything else is yours.

PyRar is provided as open source to give you the confidence you can continue your business no matter what happens.

If you are unhappy with the service at any time, we will provide you with all your data (mysql-dump & config files)
so you can move to a self-hosting instance on any public cloud. PyRar is a docker container, so there are many options for public cloud hosting.

While you are using our servce, you will need to point the Name Servers of your TLD to the Name Servers of your instance
and we will provie you with the appropriate `DS` record so you can add `DNSSEC` security to your TLDs. This is required
so your clients (SLD owners) can do `DANE` (decentralised HTTPS).


# Prices

Prices are yet to be completely finalised, but are probably going to be as follows

## Instances

All prices are per month.

All prices include
- A PyRar Server **and** a MySQL (MariaDB) Server
- Unmetered access - you will not receive any additional billing for bandwidth or data transfers.
- Unlimited 2nd line technical support for PyRar & DNS.
- 24x7 backend monitoring & maintenance by our support staff


| Size | Monthly Price | Spec |
| ---- | ------: | --- |
| Small | $75.00 | At least 10 threads |
| Medium | $150.00 | At least 25 threads |
| Large | $250.00 | Dedicated physical host, At least 50 threads |

All instances will come with one IPv4 DNS Server, in a geographic location of your choice and one IPv6 only DNS Server.

`10 threads` means 10 users can execute queries, e.g. searches, at the **exact** same time.
The 11th user's PC will automatically wait until the 1st user's query has finished, so all they will
see an hour-glass for a little longer than otherwise.

Note: All searches are done in batches of a handful at a time (configurable), so users don't have nothing happening for any significant time.

Its possible the number of threads can be extended - depending on what other services you want.


## Payment

Hosting fees are paid quarterly (in 3 month chunks) in advance, except the first payment, which must be for the first six months hosting.

There is no additional set-up fee, the first payment includes all set-up costs. Getting you set-up & helping you get to know
the system & get all external accounts set up can take some time, this is why we ask for the first 6 months hosting fees in advance.

Payment can be made by Bank Transfer (US, EU, UK & some others), PayPal, Bitcoin or Etherium.


## Optional Add-Ons

| Optional Add-On | Price|
| -- | -- |
| Additional DNS Server(s) | $25 per server, any geographic location of your choice, you can add as many as you want |
| Off-Shore Presence | $50 - your instance will only be accessible from an off-shore jurisdiction, e.g Seychelles, Morocco, Iceland |

* Additional DNS Servers will improve the DNS performance of your TLDs in the geographic location they are hosted
* Off-Shore instances can include a locally registered domain name

