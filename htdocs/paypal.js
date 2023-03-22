
// PayPal Payment plug-in JS

function paypal_startup() // {module}_startup() is a mandatory func in a JS payment module
{
	if ((gbl.config.payments)&&(gbl.config.payments.paypal)&&(gbl.config.payments.paypal.client_id))
		add_paypal_script(gbl.config.payments.paypal.client_id,gbl.config.currency.iso);

	payments["paypal"] = {
		"desc": "Pay by PayPal",
		"single": paypal_single_payment
		};

	if ((gbl.config.payments.paypal)&&(gbl.config.payments.paypal.desc))
		payments.paypal.desc = gbl.config.payments.paypal.desc;

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

		initPayPalButton(description, amount, reply.token);
		},{ json:{ "provider":"paypal"}})
}


function test_single_paypal() // this is for debugging
{
	show_one_space("userSpace")
	elm.userSpace.innerHTML = "<div id='payment-whole'></div>";
	payments.paypal.single("Test Description",1899);
}


function paypal_amount(amount) {
	let ret_js = {
		"currency_code": gbl.config.currency.iso,
		"value": format_amount(amount,true)
		};
	return ret_js;
}


function make_paypal_order(description, amount, custom_id)
{
	let ret_js = {
		purchase_units: [
			{
			"description": description,
			"custom_id": custom_id,
			"amount": paypal_amount(amount)
			}
		] };

	if ((ctx.orders)&&(ctx.orders.length > 0)) {
		let this_total = 0;
		let item_list = [];
		for(let order of ctx.orders) {
			let dom = domain_of(order.domain_id);
			this_total += order.price_paid;

			let yrs = `${order.num_years} yr`;
			if (order.num_years>1) yrs += "s";

			item_list.push({
				"name": `${order.order_type} '${dom.display_name}' for ${yrs}`,
				"quantity": 1,
				"unit_amount": paypal_amount(order.price_paid)
				});
			}

		if (ctx.user.acct_current_balance < 0) {
			item_list.push({
				"name": "Account Debt",
				"quantity": 1,
				"unit_amount": paypal_amount(-1 * ctx.user.acct_current_balance)
				});
			this_total -= ctx.user.acct_current_balance;
			}

		ret_js.purchase_units[0].items = item_list;
		ret_js.purchase_units[0].amount.breakdown = { "item_total": paypal_amount(this_total) };
		if (ctx.user.acct_current_balance > 0)
			ret_js.purchase_units[0].amount.breakdown.discount = paypal_amount(ctx.user.acct_current_balance)

		return ret_js;
		}

	ret_js.purchase_units[0].items = [ {
		"name": description,
		"quantity": 1,
		"unit_amount": paypal_amount(amount)
		} ];

	ret_js.purchase_units[0].amount.breakdown = {
		"item_total": paypal_amount(amount)
		};

	return ret_js;
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
		post_data = make_paypal_order(description, amount, custom_id);
		return actions.order.create(post_data);
	},

	onApprove: function(data, actions) {
	  return actions.order.capture().then(function(orderData) {
		console.log(orderData);
		if ((orderData)&&(orderData.purchase_units[0])&&(orderData.purchase_units[0].amount)&&(orderData.purchase_units[0].amount.value)) {
			if ((ctx.orders)&&(ctx.orders.length)) {
				callApi("payments/submitted",(ok,reply) => {
					if (ok) return do_orders_icon();
					},{ json: { "amount":from_float(orderData.purchase_units[0].amount.value) } });
				}
			}
		let e = document.getElementById("payment-whole");
		let x = '<center><h3>Thank you for your payment!</h3>'
		x += "Your payment will be processed when PayPal notifies us they have completed the transfer</center>";
		e.innerHTML = x;
	  });
	},

	onError: function(err) { 
		errMsg("PayPal processing error","errorSpan");
		console.log(err);
		}

  }).render('#payment-button');
}
