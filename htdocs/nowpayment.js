
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
	let x = "<table width=100%>"
	x += "<colgroup><col width=70%/><col/></colgroup>";
	x += "<tr><td align=center>Make payment by Crypto via NowPayment</td><td>"
	x += "<input type=button class=myBtn onClick='nowpayment_do_payment()' value='Click to Make Payment'></td></tr></table>";

	let e = document.getElementById("payment-whole");
	e.innerHTML = x;
}
