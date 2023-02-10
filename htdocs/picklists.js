
const yes_no = [ [true,"Yes"], [false,"No"] ];

const pick_lists = {
	"users" : {
		"acct_on_hold": yes_no,
		"email_verified": yes_no,
		"default_auto_renew": yes_no,
		"account_closed": yes_no
		},
	"zones" : {
		"enabled": yes_no,
		"allow_sales": yes_no
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
