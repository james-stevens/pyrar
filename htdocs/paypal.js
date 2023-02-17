

function add_paypal_script(client_id, currency) {
	let s = document.createElement('script');
	src = `https://www.paypal.com/sdk/js?client-id=${client_id}&enable-funding=venmo&currency=${currency}`;
	s.setAttribute("src", src );
	s.setAttribute("data-sdk-integration-source", "button-factory");
	document.body.appendChild( s );
}


function show_paypal()
{
	show_one_space("userSpace")
	elm.userSpace.innerHTML = '<div id="paypal-button-container"></div>';
	initPayPalButton("Test Description",12.99,"USD");
}


function initPayPalButton(description, amount, currency) {
  paypal.Buttons({
	style: {
	  shape: 'rect',
	  color: 'gold',
	  layout: 'horizontal',
	  label: 'paypal',
	  
	},

	createOrder: function(data, actions) {
	  return actions.order.create({
		purchase_units: [{"description":description,"amount":{"currency_code":currency,"value":amount}}]
	  });
	},

	onApprove: function(data, actions) {
	  return actions.order.capture().then(function(orderData) {
		
		// Full available details
		console.log('Capture result', orderData, JSON.stringify(orderData, null, 2));

		// Show a success message within this page, e.g.
		const element = document.getElementById('paypal-button-container');
		element.innerHTML = '';
		element.innerHTML = '<h3>Thank you for your payment!</h3>';

		// Or go to another URL:  actions.redirect('thank_you.html');
		
	  });
	},

	onError: function(err) {
	  console.log(err);
	}
  }).render('#paypal-button-container');
}
