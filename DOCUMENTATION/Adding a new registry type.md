# BackEnd Plug-In Functions

To add a new registry type you need to write a plug-in for it, then put
your plug-in into the directory `python/backend/dom_plugins` with the name
of the file as the name of the plug-in with the `.py` suffix.

The Python file must supply all the functions needed to control domains within that registry type,
e.g. buy a name, renew a name, update the `NS` or `DS` records, etc

## The functions you may need to supply

Except `dom/price`, all the `dom/` functions take two paramaters
- a backend job which is a dictionary of a row from the `backend` table 
- a domain object, which is a `class Domain` object from `librar/domobj.py`.

The functions should return

`True` - the function succeeded and the backend job can be deleted

`False` - the function failed, but the job can be retried

`None` - the function failed and the backend job should not be retried (it will be archived with `failures` = `9999`)


| Name | Wnat it does |
| ---- | ------------ |
| hello | takes no paramaeters, returns a "Hello World" string so you can test your plug-in is loading |
| start_up | takes no paramaeters, is run when the `backend` service starts-up |
| dom/authcode | Set a transfer AuthCode on a domain |
| dom/create | Buy a domain new |
| dom/delete | Delete a domain |
| dom/expired | Fired off when a domain expires |
| dom/flags | Fired when the user has changed the client lock flags |
| dom/info | Get the registry side information on the domain, parsed into a standarised format |
| dom/rawinfo | Get the registry side information on the domain in the registry native format |
| dom/recover | Recover a domain, ie. renew a domain that has passed its expiry date |
| dom/renew | Renew a domain |
| dom/transfer | Transfer a domain to this user with the AuthCode supplied in the `backend` record |
| dom/update | Fired when the user has updated the `NS` or `DS` fields |


## dom/price

`dom/price` is special, in that it takes & returns completely different parameters.
This function is used for checking domain prices and domain purchase availability.

Parameters:-
- `domlist` : a `class DomainList` object from `librar/domobj.py`
- `num_years` : an integer of the number of years to get a price for
- `qry_type` :  A list of the type of actions you want a price on, these can be `create` (new), `renew`, `transfer` or `recover`

The list of domains supplied in `domlist` should always be from the same registry operator, as defined in `registry.json`.
this does not mean they have to be in the same parent domains (TLDs), just hosted at the same registry operator.

If `num_years` is not supplied it should default to `1`

If `qry_type` is not supplied it should default to `["create", "renew"]`

The function should return a list of dictionaries of the domains, their prices and class as the following properties
- `name` : the domain name
- `num_years` : The number of years the price is for
- `avail` : Boolean, if the domain is available for registration or not
- `class` : The price class of the domain, `standard` should be the default if the domain is not a premium proiced name

The price is then specified as a floating point number with each `qry_type` as the property name and the price as the property value, e.g.

      {
         "avail": true,
         "class": "standard",
         "num_years": 1,
         "create": "30.00",
         "renew": "30.00",
         "name": "name.example"
      }


The prices supplied by the plug-in should be the **RAW** price charged by the registry system. 
PyRar will automatically apply the reseller mark-up you have specified.

You can test the prices function by running

	./run_backend.py -a dom/price -d <domain-name>


If a particlar function is not required, you can either not define it, or define it as `None`.
Nothing will be happy if you do not supply the `dom/price` function.


The plug-in is added to the system by adding its function with a call to `dom_handler.add_plugin`.
This should be called in the plug-in when it is imported by the backend.

`dom_handler.add_plugin` takes two parameteres
- A string which is the name of this plug-in and should match the python file name
- A dictionary of the functions

This is the call to add the `local` plug-in

	dom_handler.add_plugin(
		"local", {
			"hello": my_hello,
			"start_up": start_up_check,
			"dom/update": domain_update_from_db,
			"dom/create": domain_create,
			"dom/renew": domain_renew,
			"dom/transfer": domain_request_transfer,
			"dom/delete": domain_delete,
			"dom/expired": domain_expired,
			"dom/info": domain_info,
			"dom/rawinfo": domain_info,
			"dom/recover": domain_recover,
			"dom/price": local_domain_prices
		})


`dom_handler` is imported from `backend`

	from backend import dom_handler

Juts take a look through the `local` plug-in at `python/backend/dom_plugins/local.py` for more info.
