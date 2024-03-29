
const yes_no = [ [true,"Yes"], [false,"No"] ];

pick_lists = {
	"users" : {
		"acct_on_hold": yes_no,
		"email_verified": yes_no,
		"default_auto_renew": yes_no,
		"account_closed": yes_no
		},
	"zones" : {
		"enabled": yes_no,
		"allow_sales": yes_no,
		"renew_limit": [
			[ 0, "Unlimited"],
			[ 1, "1 Year" ],
			[ 2, "2 Years" ],
			[ 3, "3 Years" ],
			[ 4, "4 Years" ],
			[ 5, "5 Years" ],
			[ 6, "6 Years" ],
			[ 7, "7 Years" ],
			[ 8, "8 Years" ],
			[ 9, "9 Years" ],
			[ 10, "10 Years" ],
			[ 11, "11 Years" ],
			]
		},
	"domains" : {
		"auto_renew": yes_no,
		"status_id" : [
			[ 1 , "Live" ],
			[ 10 , "Awating Payment" ],
			[ 11 , "Processing" ],
			[ 20 , "Expired" ],
			[ 100 , "Transfer Queued" ],
			[ 101 , "Transfer Requested" ],
			[ 120 , "Transfer Failed" ],
			[ 200, "Reserved" ],
			],
		"auto_renew": yes_no
	}
};


function find_pick_value(table,column,value)
{
	if (!pick_lists[table]) return value;
	if (!pick_lists[table][column]) return value
	for(let i of pick_lists[table][column])
		if (value == i[0]) return `${i[1]} (${value})`;
	return value;
}
