# `etc` is to configure `pyrar` how you want

You will need to edit the files `logins.json`, `policy.json`, `priority.json`, `registry.json`.
The `example` files are there to help you.


# Logins

This holds the credentials for all logins. You will need to edit this to configure the logins to your MySQL
and any logins you have for EPP registrars.

The MySQL logins (for pyrar & pdns) have been entered as templates, all you need to do is fill them out.

If you only have a single login to your PyRar MySQL database, copy the template for `admin` for the other logins.
It would be better if the WebUI MySQL login was separate, so it does not have permission to drop tables,
but if you only have one login that's what you have.

`[PYRAR-DATABASE-SERVER]` and `[PDNS-DATABASE-SERVER]` will be the host name/ IP Address of the MySQL Server.


# Policy

You will need to customise all the items in the template in this file. There are many other `policy` items
you can change to tweak the behaviour of PyRar, many can be seen in the source code in `python/librar/policy.py`.

Your `catalog_zone` should be a valid host name in two parts, ending `.localhost`, like `my-name.localhost`

If you do not have a Syslog Server, then set this to `null` and PyRar will log to its console.
This is probably not useful, but better than nothing.

Emails are send out as `From: [name_sender] <email_sender>` but (if undelivered) will bounce back to `email_return`.

The default is to account in `USD`, if this is not what you want, then you need to set a different `currency` in
the `policy.json` file. The `currency` has a number of fields

This is what the configuration for USD looks like

    "currency" : {
        "desc": "US Dollars",
        "iso": "USD",
        "symbol": "$",
        "separator": [",","."],
        "decimal": 2
        }

If you wanted to account in Ethereum, it would look like this

    "currency" : {
        "desc": "Ethereum",
        "iso": "ETH",
        "symbol": "Ξ",
        "separator": [",","."],
        "decimal": 6
        }



# Registry

This file lists all the registries you want to sell domains from. Each will have a `type` which can be `epp` or `local`.
If you want the same prices for all domains from that registry, then you can set that here. If not
then when you add the TLDs to the `zones` table you can set the prices on a TLD by TLD basis.

For EPP regitries you will probably want to take their price & apply a margin either by adding or multiply it, 
e.g. `x1.5` or `+10.00`.

If you are accounting in a different currency from the registry you are buying from, then you will need
to include the currency conversion factor in the `prices` adjustor, as well as allowing for adding your margin.


# Priority

This is a simple list of the TLD (from the `zones` table) that you want to be given priority when the user
does a search. This may be the ones you personally own, the best selling ones or ones that have been newly introduced.

All the other files are JSON objects, this is just a list.
