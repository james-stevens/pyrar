
const theme_colours = {
	"blue": [
		"000000","383855","4f4f6f","555577","666688",
		"666699","777799","8888aa","9999bb","a0a0cc",
		"aaaacc","b0b0ff","c0c0e0","d0d0ff","ddddff",
		"ffd0d0","ffffff","8888aa"
		],
	"red": [
		"000000","553838","6f4f4f","775555","886666",
		"996666","997777","aa8888","bb9999","cca0a0",
		"ccaaaa","ffb0b0","e0c0c0","ffd0d0","ffdddd",
		"d0d0ff","ffffff","aa8888"
		],
	"green": [
		"000000","385538","4f6f4f","557755","668866",
		"669966","779977","88aa88","99bb99","a0cca0",
		"aaccaa","b0ffb0","c0e0c0","d0ffd0","ddffdd",
		"d0d0ff","ffffff","88aa88"
		],
	"light": [
		"000000","555555","F0F2F4","F6F8FA","ffffff",
		"999999","F6F8FA","aaaaaa","F0F2F4","cccccc",
		"cccccc","9898ff","e0e0e0","cccccc","ffffff",
		],
	"dark": [
		"C9D1D9","555555","25303B","010409","15202B",
		"999999","25303B","464B52","35404B","464B52",
		"464B52","9898ff","e0e0e0","767B92","ffffff",
		"ffd0d0","C9D1D9","25303B"
		],
	"custom": [
		"C9D1D9","555555","25303B","010409","15202B",
		"999999","25303B","464B52","35404B","464B52",
		"464B52","9898ff","e0e0e0","767B92","ffffff",
		"ffd0d0","C9D1D9","25303B"
		]
	};



function changeTheme(theme_name)
{
	gbl.theme = theme_name;
	document.querySelector("style").innerText = theme_css(theme_name);
}


function theme_css(theme) {
	let cols = theme_colours[theme];
	return `
.fullvis { font-family:inherit; font-size:14pt; visibility: visible; opacity: 1; text-align: center; }
.fadein  { font-family:inherit; font-size:14pt; visibility: visible; opacity: 1; transition: opacity 0.5s linear; }
.fadeout { font-family:inherit; font-size:14pt; visibility: hidden; opacity: 0; transition: visibility 0s 1s, opacity 1s linear; }

::placeholder {
	color: #${cols[12]};
	opacity: 1; }

.topLink { font-size: 20px; }
h2 { text-align: center; }

.btmBtnBar {
	text-align: center;
	padding-top: 10px;
	padding-bottom: 10px;
	border: 1px solid;
	border-color: #${cols[7]};
	border-radius: 6px;
	}

#topSpan{
	background-color: #${cols[6]};
	height: 55px;
	line-height: 55px;
	margin-top: 0px;
	padding-left: 0px;
	padding-top: 1px;
	top: 0px;
	}

html {
	color: #${cols[16]};
	font-family:Verdana,Arial,Helvetica,sans-serif;
	font-size: 14px;
	background-color: #${cols[4]};
	scrollbar-base-color: #${cols[5]};
	scrollbar-arrow-color: #${cols[14]};
	}

th {
	color: #${cols[0]};
	font-family: inherit;
	font-size: 18px;
	background-color: #${cols[9]};
	font-weight: bold;
	padding-left: 6px;
	padding-right: 6px;
	}

select {
	padding: 5px 12px;
	background-color: #${cols[3]};
	color: #${cols[16]};
	font-family: inherit;
	font-size: 14px;
	border-radius: 6px;
	border: 1px solid;
	border-color: #${cols[7]};
}

input {
	padding: 5px 12px;
	background-color: #${cols[3]};
	color: #${cols[16]};
	font-family: inherit;
	font-size: 14px;
	border-radius: 6px;
	border: 1px solid;
	border-color: #${cols[7]};
	}

.inputBad {
	color: #${cols[0]};
	background-color: #${cols[15]};
	font-family: inherit;
	font-size: 14px;
	}

body {
	color: #${cols[16]};
	font-family: inherit;
	font-size: inherit;
	margin-top: 0px;
	margin-left: 0px;
	margin-right: 0px;
	background-color: #${cols[4]};
	scrollbar-base-color: #${cols[5]};
	scrollbar-arrow-color: #${cols[14]};
	}


a {
	color: #${cols[11]};
	text-decoration:none;
	}

a:hover {
	text-decoration: underline;
	}

form {
	margin:0px;
	}

.myBtn {
	text-align: center;
	display: inline-block;
	background-color: #${cols[17]};
	color: #${cols[16]};
	font-family: inherit;
	font-size: 14px;
	border-radius: 6px;
	border: 1px solid;
	border-color: #${cols[10]};
	padding: 5px 16px;
	cursor: pointer;
	margin-top: 0px;
	margin-left: 10px;
	margin-bottom: 2px;
	margin-right: 2px;
	}

.myBtn:hover {
	border-color: #${cols[13]};
	background-color: #${cols[8]};
	}

.myBtn:active {
	position: relative;
	box-shadow: none;
	text-shadow: none;
	top: 1px;
	left: 1px;
	}

.dnskey {
	color: #${cols[1]};
	}

td {
	font-family:inherit;
	font-size: 14px;
	vertical-align: top;
	padding-left: 7px;
	padding-right: 7px;
	white-space: nowrap;
	}

.dataCell {
	font-family:inherit;
	font-size: 14px;
	vertical-align: top;
	padding-left: 7px;
	padding-right: 7px;
	white-space: normal;
	min-width: 50%;
	overflow-wrap: anywhere;
	}

.dataRow {
	font-family: inherit;
	font-size: 14px;
	cursor: pointer;
	color: #${cols[16]};
	background-color: #${cols[4]};
	}

.dataRow:hover {
	background-color: #${cols[2]};
	}


.formPrompt {
	font-family:inherit;
	font-size: 14px;
	color: #${cols[16]};
	text-align: right;
	padding-top: 8px;
	}


.msgPop {
	position: absolute;
	left: 10px;
	top: 20px;
	font-family:inherit;
	font-size:16pt;
	width: 95%;
	background: #${cols[15]};
	text-align: center;
	color: #${cols[0]};
	padding: 5px;
	border-radius: 6px;
	}

.msgPopNo {
	visibility: hidden;
	opacity: 0; transition: visibility 0s 1s, opacity 1s linear;
	}

.msgPopYes {
	visibility: visible;
	opacity: 1; transition: opacity 0.5s linear;
	}
`;
}
