
// PayPal Payment plug-in JS

function paypal_startup() // {module}_startup() is a mandatory func in a JS payment module
{
	if ((gbl.config.payment)&&(gbl.config.payment.paypal)&&(gbl.config.payment.paypal.client_id))
		add_paypal_script(gbl.config.payment.paypal.client_id,gbl.config.currency.iso);

	payments["paypal"] = {
		"desc": "PayPal",
		"single": paypal_single_payment
		};
}


function add_paypal_script(client_id, currency) {
	let s = document.createElement('script');
	src = `https://www.paypal.com/sdk/js?client-id=${client_id}&enable-funding=venmo&currency=${currency}`;
	s.setAttribute("src", src );
	s.setAttribute("data-sdk-integration-source", "button-factory");
	document.body.appendChild( s );
}



function paypal_single_payment(description, amount)
{
	callApi("payments/single",(ok,reply)=> {
		if (!ok) return def_errMsg("Failed to create single use token",reply,"payment-whole");

		let x = "<table width=100%>"
		x += "<colgroup><col width=70%/><col/></colgroup>";
		x += "<tr><td align=center>Make payment by PayPal</td><td><span id='payment-button'></span></td></tr></table>";

		let e = document.getElementById("payment-whole");
		e.innerHTML = x;

		initPayPalButton(description, amount, reply.provider_tag);
		},{ json:{ "provider":"paypal"}})
}


function test_single_paypal() // this is for debugging
{
	show_one_space("userSpace")
	elm.userSpace.innerHTML = "<div id='payment-whole'></div>";
	payments.paypal.single("Test Description",18.99);
}



function initPayPalButton(description, amount, custom_id) {
  paypal.Buttons({
	style: {
	  shape: 'rect',
	  color: 'gold',
	  layout: 'horizontal',
	  label: 'paypal',
	  
	},

	createOrder: function(data, actions) {
	  return actions.order.create({
		purchase_units: [
			{
			"description": description,
			"custom_id": custom_id,
			"amount":{
				"currency_code": gbl.config.currency.iso,
				"value": amount
				}
			}
		]
	  });
	},

	onApprove: function(data, actions) {
	  return actions.order.capture().then(function(orderData) {
		// console.log(orderData);
		let e = document.getElementById("payment-whole");
		let x = '<center><h3>Thank you for your payment!</h3><br>'
		x += "Your payment will be processed<br>when PayPal notifies us they have completed the transfer</center>";
		e.innerHTML = x;
	  });
	},

	onError: function(err) { errMsg(err,"payment-whole"); }

  }).render('#payment-button');
}
