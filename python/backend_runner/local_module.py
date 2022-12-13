#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information


BACKEND_JOB_FUNC = {
    "start_up": start_up_check,
    "dom/update": domain_update_from_db,
    "dom/create": domain_create,
    "dom/renew": domain_renew,
    "dom/transfer": domain_request_transfer,
    "dom/authcode": set_authcode
}
