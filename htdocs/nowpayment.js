
// NowPayments Payment plug-in JS

let nowpayment_win = null;

function nowpayment_startup() // {module}_startup() is a mandatory func in a JS payment module
{
    if ((!gbl.config.payments)||(!gbl.config.payments.nowpayment)) return;
    let my_conf = gbl.config.payments.nowpayment;
    payments["nowpayment"] = {
        "desc": "Pay by Crypto via NowPayments",
        "single": nowpayment_single_payment
        };

    if (my_conf.desc) payments.nowpayment.desc = my_conf.desc;
}



function nowpayment_single_payment(description, amount)
{
	nowpayment_win = null;
	let x = "<table border=0 align=center>";
	x += "<colgroup><col width=70%/><col/></colgroup>";
	x += "<tr><td align=center>Make payment by Crypto via NowPayments</td>";
	x += `<td><input type=button class=myBtn onClick='nowpayment_do_payment("${description}",${amount})' value='Click to Make Payment'></td></tr>`;
	x += "<tr><td colspan=2>"+gbl.gap+"</td></tr>";
	x += "<tr><td colspan=2>If NowPayments says your <a target=_blank href='https://nowpayments.io/status-page'>amount is too small</a>, try paying with a different crypto currency</td></tr>";
	x += "</table>";
	let e = document.getElementById("payment-whole");
	e.innerHTML = x;
}



function nowpayment_done()
{
	if (nowpayment_win) {
		nowpayment_win.close();
		nowpayment_win = null;
		}
	nowpayment_show_end_message();
	clearTimeout(gbl.msmTimer);
	gbl.msmTimer = setTimeout(check_for_messages,5000);
}


function nowpayment_show_end_message()
{
	let x = "<table border=0 align=center>";
	x += "<tr><td>Your payment was succcessful your account will be credited as soon as we are notified</td></tr>";
	x += "</table>";
	let e = document.getElementById("payment-whole");
	e.innerHTML = x;
}



function nowpayment_do_payment(description, amount)
{
    callApi("payments/single",(ok,reply)=> {
        if (!ok) return def_errMsg("Failed to create NowPayments Invoice",reply,"payment-whole");
        nowpayment_win = window.open(reply.invoice_url,"nowpayment");
        nowpayment_win.focus();
        },{ json:{ "provider":"nowpayment","description":description, "amount":amount }})
}
