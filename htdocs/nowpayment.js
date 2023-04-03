
// NowPayment Payment plug-in JS

function nowpayment_startup() // {module}_startup() is a mandatory func in a JS payment module
{
    if ((!gbl.config.payments)||(!gbl.config.payments.nowpayment)) return;
    let my_conf = gbl.config.payments.nowpayment;
    payments["nowpayment"] = {
        "desc": "Pay by Crypto via NowPayment",
        "single": nowpayment_single_payment
        };

    if (my_conf.desc) payments.nowpayment.desc = my_conf.desc;
}

function nowpayment_single_payment(description, amount)
{
	let x = "<table border=0 align=center>";
	x += "<colgroup><col width=70%/><col/></colgroup>";
	x += "<tr><td align=center>Make payment by Crypto via NowPayment</td>";
	x += `<td><input type=button class=myBtn onClick='nowpayment_do_payment("${description}",${amount})' value='Click to Make Payment'></td></tr>`;
	x += "<tr><td colspan=2>"+gbl.gap+"</td></tr>";
	x += "<tr><td colspan=2>If NowPayment says your amount is too small, try paying with a different crypto currency</td></tr>";
	x += "</table>";
	let e = document.getElementById("payment-whole");
	e.innerHTML = x;
}

let nowpayment_win = null;
let nowpayment_timer = null;

function nowpayment_done()
{
	nowpayment_win.close();
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
        if (!ok) return def_errMsg("Failed to create NowPayment Invoice",reply,"payment-whole");
        nowpayment_win = window.open(reply.invoice_url,"nowpayment");
        nowpayment_win.focus();
        },{ json:{ "provider":"nowpayment","description":description, "amount":amount }})
}
