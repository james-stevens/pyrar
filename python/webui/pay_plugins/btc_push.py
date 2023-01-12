#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information

from librar import validate
from webui import pay_handler
from librar import mysql as sql

from librar.policy import this_policy as policy


def btc_push_html(user_id):
    currency = policy.policy("currency")
    html = """<table align=center cellspacing=1 cellpadding=0 border=0>
        <tr><td style='white-space: normal;' colspan=2>Bitcoin Push payment means you can send credits into
        your account at any time, but we can not request money from your Bitcoin account.
        We will have to rely on you to send money.<P>
        If you enable automatic renewal on any of your domains, 
        and you have verified your account email address, we will send an email to your account
        email address to tell you when you need to send money.<P>
        Money in your account will be held, and account for, in """ + currency["desc"] + """
        </td></tr>
        <tr><td colspan=2><div style='height: 15px;'></div></td></tr>
        <tr>
            <td class=formPrompt>Bitcoin wallet you will send payments from :</td>
            <td><input id='pay.provider_tag' style='width: 350px;'></td>
        </tr>
        <input type=hidden id="pay.single_use" value=0>
        <input type=hidden id="pay.can_pull" value=0>
        <input type=hidden id="pay.provider" value="btc_push">
        <tr><td colspan=2><div style='height: 15px;'></div></td></tr>
        <tr><td colspan=2 class=btmBtnBar><input
            onClick='click_add_payment();'
            class=myBtn
            type=button
            style='width: 175px;'
            value="Add Bitcoin Push"></td></tr>
        </table>"""
    return True, html


def btc_push_validate(data):
    data["single_use"] = 0
    data["can_pull"] = 0
    data["provider"] = "btc_push"
    return True


pay_handler.add_plugin("btc_push", {
    "desc": "Bitcoin Push",
    "html": btc_push_html,
    "validate": btc_push_validate
})
