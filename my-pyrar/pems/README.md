# Put your PEM files here

## EPP Client PEMs

You will need one client PEM file for each registry you are connecting to over EPP.
The PEM file must be installed as `pems/<registry-name>.pem` where `registry-name` is what you called
the registry in `etc/registry.json`.

In the example file `etc/example_registry_one_epp_one_local.json` the EPP registry is called `namereg`
so the PEM file for that registry would be `pems/namereg.pem`.

If you wish to use the same client PEM file for more than one registry you will need to copy it, or use symlinks.

Different registries have different rules on client certificates, so you need to consult their documentation.


## Server PEM

If you include a file called `pems/server.pem` then the nginx in `pyrar` will run in HTTPS (instead of HTTP) mode.

On some hosting platforms its common to run HTTP on your service and they do the HTTPS on an external proxy.

NOTE: the `server.pem` will need to be updated as it expires.
