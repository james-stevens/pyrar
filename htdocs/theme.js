
const theme_colours = {
	"dark": [
		"C9D1D9","555555","45505B","010409","15202B",
		"999999","25303B","464B52","35404B","464B52",
		"464B52","9898ff","808080","767B92","ffffff",
		"ffd0d0","C9D1D9","25303B","010409"
		],
	"light": [
		"000000","555555","F0F2F4","F6F8FA","ffffff",
		"999999","F6F8FA","aaaaaa","F6F8FA","cccccc",
		"cccccc","9898ff","e0e0e0","303030","ffffff",
		"000000","000000","F0F2F4","d6d8dA"
		],
	"blue": [
		"000000","383855","4f4f6f","555577","666688",
		"666699","777799","8888aa","9999bb","a0a0cc",
		"aaaacc","b0b0ff","8080b0","d0d0ff","ddddff",
		"ffd0d0","ffffff","8888aa","555577"
		],
	"red": [
		"000000","553838","6f4f4f","775555","886666",
		"996666","997777","aa8888","bb9999","cca0a0",
		"ccaaaa","ffb0b0","b08080","ffd0d0","ffdddd",
		"d0d0ff","ffffff","aa8888","775555"
		],
	"green": [
		"000000","385538","4f6f4f","557755","668866",
		"669966","779977","88aa88","99bb99","a0cca0",
		"aaccaa","b0ffb0","80b080","d0ffd0","ddffdd",
		"d0d0ff","ffffff","88aa88","557755"
		],
	"default": [
		"C9D1D9","555555","25303B","010409","15202B",
		"999999","25303B","464B52","35404B","464B52",
		"464B52","9898ff","e0e0e0","767B92","ffffff",
		"ffd0d0","C9D1D9","25303B","010409"
		]
	};



function changeTheme(theme_name)
{
	if (!(theme_name in theme_colours)) return;

	gbl.theme = theme_name;
	window.localStorage.setItem("theme",gbl.theme);
	document.querySelector("style").innerText = theme_css(theme_name);
}


function theme_css(theme) {
	let cols = theme_colours[theme];
	return `
.fullvis { font-family:inherit; font-size:14pt; visibility: visible; opacity: 1; text-align: center; }
.fadein  { font-family:inherit; font-size:14pt; visibility: visible; opacity: 1; transition: opacity 0.5s linear; }
.fadeout { font-family:inherit; font-size:14pt; visibility: hidden; opacity: 0; transition: visibility 0s 1s, opacity 1s linear; }


.emoji {
	text-align: center;
	display: inline-block;
	background-color: #${cols[17]};
	color: #${cols[16]};
	font-family: inherit;
	border-radius: 6px;
	border: 1px solid;
	border-color: #${cols[10]};
	font-size: 25px;
	cursor: pointer;
	width: 70px;
	white-space: nowrap;
	padding: 1px 7px;
	margin-top: 0px;
	margin-left: 0px;
	margin-bottom: 0px;
	margin-right: 0px;
	text-overflow: clip;
	overflow-x: hidden;
	}

.emoji:hover {
	border-color: #${cols[13]};
	background-color: #${cols[8]};
	}


.userIcons {
	margin-right: 10px;
	cursor: pointer;
	font-size: 22px;
	}

.botSpace {
	min-width: 75%;
	margin-left: auto;
	margin-right: auto;
	background-color: #${cols[4]};
	border: 1px solid;
	border-color: #${cols[10]};
	box-shadow: 3px 3px #${cols[18]};
	padding: 10px;
	border-radius: 6px;
	}

::placeholder {
	color: #${cols[12]};
	opacity: 1; }

.topLink { font-size: 20px; }
h2 { text-align: center; }

.line {
	background: #${cols[7]};
	width: 100%;
	height: 1px;
	}

.btmBtnBar {
	text-align: center;
	padding-top: 10px;
	padding-bottom: 10px;
	border: 1px solid;
	border-color: #${cols[7]};
	border-radius: 6px;
	}


.searchDomain { font-size: 20px; }
.searchDomain:hover { background-color: #${cols[6]}; }

.searchRenew {
	font-size: 12px;
	color: #${cols[1]};
	}

.windowBanner {
	font-weight: bold;
	font-size: 18px;
	padding: 7px;
	border-bottom: 1px solid #${cols[7]};
	}

.settingsBanner {
	font-weight: bold;
	font-size: 18px;
	padding: 7px;
	border-bottom: 1px solid #${cols[6]};
	}

.pageHeading {
	font-weight: bold;
	font-size: 25px;
	padding: 7px;
	text-align: center;
	border-bottom: 1px solid #${cols[6]};
	}

#topSpan{
	position: fixed;
	z-index: 100;
	top: 0;
	width: 100%;
	background-color: #${cols[6]};
	height: 100px;
	line-height: 100px;
	margin-top: 0px;
	padding-left: 0px;
	padding-top: 1px;
	}

#businessName {
	font-weight: bold;
	padding-left: 30px;
	font-size: 25px;
	margin-left: 10px;
	}

#businessName a {
	color: #${cols[16]};
	}

#businessName a:hover {
    text-decoration: none;
	color: #${cols[11]};
	}


.userMsg {
	padding: 30px;
	font-size: 32px;
	margin-top: 50px;
	text-align: center;
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
	font-weight: normal;
	background-color: #${cols[6]};
	padding-left: 6px;
	padding-right: 6px;
	white-space: nowrap;
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

.searchBox {
	padding: 5px 12px;
	background-color: #${cols[3]};
	color: #${cols[16]};
	font-family: inherit;
	font-size: 20px;
	border-radius: 6px;
	border: 1px solid;
	border-color: #${cols[7]};
	width: 100%;
	}

.inputBad {
	color: #${cols[0]};
	background-color: #${cols[15]};
	font-family: inherit;
	font-size: 14px;
	}

#allBottom {
	display: flex;
	justify-content: center;
	margin-top: 20px;
	background-size: 100% 100%;
	}

body {
	color: #${cols[16]};
	font-family: inherit;
	font-size: inherit;
	margin-top: 0px;
	margin-left: 0px;
	margin-right: 0px;
	margin-bottom: 0px;
	height: 100%;
	width: 100%;
	scrollbar-base-color: #${cols[5]};
	scrollbar-arrow-color: #${cols[14]};

	background-color: #${cols[4]};
	background-image: url("/img/bg-${theme}.jpg");
	background-size: contain;
	background-size: 100vw 100vh;
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
	cursor: pointer;
	padding: 5px 16px;
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
	font-size: inherit;
	vertical-align: top;
	padding-left: 7px;
	padding-right: 7px;
	white-space: nowrap;
	}

.promptCell {
	font-weight: bold;
	font-family:inherit;
	font-size: inherit;
	vertical-align: top;
	padding-left: 7px;
	padding-right: 7px;
	padding-top: 2px;
	white-space: normal;
	min-width: 50%;
	white-space: nowrap;
	text-align: right;
	}

.dataCell {
	font-family:inherit;
	font-size: inherit;
	vertical-align: top;
	padding-left: 7px;
	padding-right: 7px;
	white-space: normal;
	min-width: 50%;
	white-space: nowrap;
	}

.dataRow {
	font-family: inherit;
	font-size: 14px;
	cursor: pointer;
	color: #${cols[16]};
	background-color: #${cols[4]};
	text-overflow: clip;
	}

.dnsData {
	text-overflow: ellipsis;
	overflow-x: clip;
	max-width: 1px;
	}

.dataRow:hover { background-color: #${cols[2]}; }

.dataRowBig {
	font-family: inherit;
	font-size: 16px;
	cursor: pointer;
	color: #${cols[16]};
	background-color: #${cols[4]};
	}

.dataRowBig:hover { background-color: #${cols[2]}; }


.formPrompt {
	font-family:inherit;
	font-size: 14px;
	color: #${cols[16]};
	text-align: right;
	padding-top: 8px;
	}


.msgPop {
	z-index: 200;
	position: absolute;
	font-family:inherit;
	font-size: 16pt;
	width: 95%;
	background: #${cols[15]};
	text-align: center;
	color: #${cols[0]};
	padding: 5px;
	border-radius: 6px;
	width: auto;
	}

.msgPopNo {
	visibility: hidden;
	opacity: 0; transition: visibility 0s 1s, opacity 1s linear;
	}

.msgPopYes {
	visibility: visible;
	opacity: 1; transition: opacity 0.5s linear;
	}

/* Popup container */
.popup {
	position: relative;
	display: inline-block;
	cursor: pointer;
}

/* The actual popup (appears on top) */
.popBelow .popBelowText {
	visibility: hidden;
	background-color: #${cols[6]};
	color: #fff;
	border-radius: 6px;
	padding: 8px;
	position: absolute;
	z-index: 1;
	height: 175px
	left: 75%;
	margin-left: -120;
	margin-top: 30px;
	border: 1px solid;
	border-color: #${cols[10]};
	box-shadow: 3px 3px #${cols[18]};
	}

/* Toggle this class when clicking on the popup container (hide and show the popup) */
.popBelow .show {
	visibility: visible;
	-webkit-animation: fadeIn 1s;
	animation: fadeIn 1s
	}

/* The actual popup (appears on top) */
.popup .popuptext {
	visibility: hidden;
	background-color: #${cols[6]};
	color: #fff;
	border-radius: 6px;
	padding: 8px;
	position: absolute;
	z-index: 1;
	height: 175px
	left: 75%;
	margin-left: -350px;
	margin-top: 30px;
	border: 1px solid;
	border-color: #${cols[10]};
	box-shadow: 3px 3px #${cols[18]};
	}

/* Toggle this class when clicking on the popup container (hide and show the popup) */
.popup .show {
	visibility: visible;
	-webkit-animation: fadeIn 1s;
	animation: fadeIn 1s
	}

/* Add animation (fade in the popup) */
@-webkit-keyframes fadeIn {
	from {opacity: 0;}
	to {opacity: 1;}
	}

@keyframes fadeIn {
	from {opacity: 0;}
	to {opacity:1 ;}
	}

#noLoginBtns {
	margin-right: 50px;
	}

#isLoggedIn {
	margin-right: 50px;
	}

#userInfo {
	margin-right: 50px;
	}

.fullvis { font-family:inherit; font-size:14pt; visibility: visible; opacity: 1; text-align: center; }
.fadein  { font-family:inherit; font-size:14pt; visibility: visible; opacity: 1; transition: opacity 0.5s linear; }
.fadeout { font-family:inherit; font-size:14pt; visibility: hidden; opacity: 0; transition: visibility 0s 1s, opacity 1s linear; }

.msgPop {
	position: absolute;
	left: 10px;
	top: 20px;
	font-family:inherit;
	font-size:16pt;
	background: #${cols[2]};
	text-align: center;
	color: #${cols[16]};
	padding: 5px;
	border-radius: 6px;
	box-shadow: 3px 3px #${cols[18]};
	}

.msgPopNo {
	visibility: hidden;
	opacity: 0; transition: visibility 0s 1s, opacity 1s linear;
	}

.msgPopYes {
	visibility: visible;
	opacity: 1; transition: opacity 0.5s linear;
	}


`.replace(/[\n\t]/g,"");
}
