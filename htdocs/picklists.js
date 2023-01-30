
const yes_no = [ [1,"Yes"], [0,"No"] ]

const pick_lists = {
	"users" : {
		"acct_on_hold": yes_no,
		"email_verified": yes_no,
		"default_auto_renew": yes_no,
		"account_closed": yes_no
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
			[ 120 , "Transfer Failed" ]
			],
		"auto_renew": yes_no
	}
}
