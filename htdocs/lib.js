
// add a trailing '.' for these record types, if the user forgets
const autoAddDot = { rrMX: true, rrNS: true, rrCNAME: true, };

// regex for an FQDN hostname
const fqdnCheck = /^(([a-zA-Z0-9_]|[a-zA-Z0-9_][a-zA-Z0-9\-_]*[a-zA-Z0-9_])\.)*(xn--|)[A-Za-z0-9\-]+$/;

// regex for adding a host name
const hostnameCheck = /^([a-zA-Z0-9_*]|[a-zA-Z0-9_][a-zA-Z0-9\-_]*[a-zA-Z0-9_])(\.([a-zA-Z0-9_]|[a-zA-Z0-9_][a-zA-Z0-9\-_]*[a-zA-Z0-9_]))*$/

const valid_email = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;

// regex's for RR validation - just add more here and they will work
const validations = {
	rrAAAA: /^(([0-9A-F]{1,4}:){7,7}[0-9A-F]{1,4}|([0-9A-F]{1,4}:){1,7}:|([0-9A-F]{1,4}:){1,6}:[0-9A-F]{1,4}|([0-9A-F]{1,4}:){1,5}(:[0-9A-F]{1,4}){1,2}|([0-9A-F]{1,4}:){1,4}(:[0-9A-F]{1,4}){1,3}|([0-9A-F]{1,4}:){1,3}(:[0-9A-F]{1,4}){1,4}|([0-9A-F]{1,4}:){1,2}(:[0-9A-F]{1,4}){1,5}|[0-9A-F]{1,4}:((:[0-9A-F]{1,4}){1,6})|:((:[0-9A-F]{1,4}){1,7}|:)|fe80:(:[0-9A-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9A-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$/i,
	   rrA: /^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$/,
	  rrMX: /^[1-9][0-9]{0,5} (([a-zA-Z0-9_]|[a-zA-Z0-9_][a-zA-Z0-9\-_]*[a-zA-Z0-9_])\.)+([A-Za-z0-9_]|[A-Za-z0-9_][A-Za-z0-9\-_]*[A-Za-z0-9_])[.]$/,
	  rrNS: fqdnCheck,
   rrCNAME: fqdnCheck,
 rrCATALOG: fqdnCheck,
	  rrDS: /^(([123456]?[0-9]{1,4}|[0-9]1,4) ([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]) [1234] [0-9A-F ]{40,100})$/i,
	};

const pow10 = { 0:1, 1:10, 2:100, 3:1000, 4:10000, 5:100000, 6:1000000, 7:10000000, 8:100000000, 9:1000000000, 10:10000000000 };

function from_float(amount)
{
	return Math.round(parseFloat(amount)*pow10[gbl.config.currency.decimal]);
}


function callApi(sfx,callback,inData)
{
	document.body.style.cursor="progress";
	elm.topMsg.innerHTML = `Loading ... ${gbl.timer}`;

	function we_are_done(ok,reply)
	{
		document.body.style.cursor="auto";
		elm.topMsg.innerHTML = "";
		return callback(ok,reply);
	}

	function check_session(headers)
	{
		let got_ses = false;
		headers.forEach((val, key) => {
			if (key=="x-session-code") {
				got_ses = true;
				if (!("session" in ctx)) {
					window.localStorage.setItem("session",val);
					ctx.session = val;
					loggedIn();
					}
				}
			});

		if ((!got_ses)&&("session" in ctx)) {
			window.localStorage.removeItem("session");
			ctx = {};
			loggedOut();
			}
	}

	if (debugAPI) { console.log("API>>>",sfx); console.log("API>>>",inData); }

	let url = `${window.location.origin}/pyrar/v1.0/${sfx}`;
	if (gbl.url_prefix)
		url = `${window.location.origin}${gbl.url_prefix}${sfx}`;
	if (sfx.slice(0,1)=="/")
		url = `${window.location.origin}${sfx}`;

	let okResp = 200;
	let httpCmd = { headers: { }, method: 'GET' };

	if (inData != null) {
		if ("json" in inData) {
			httpCmd.body = JSON.stringify(inData.json);
			httpCmd.headers["Content-type"] = "application/json; charset=UTF-8";
			httpCmd.method = "POST";
			}
		if ("okResp" in inData) okResp = inData.okResp;
		if ("method" in inData) httpCmd.method = inData.method;
		}

	if ("session" in ctx) {
		httpCmd.headers["X-Session-Code"] = ctx.session
	} else {
		let s = window.localStorage.getItem("session");
		if (s != null) {
			httpCmd.headers["X-Session-Code"] = s;
			ctx.session = s;
			}
		}
	if (debugAPI) { console.log("OUT-HEAD",httpCmd.headers); console.log("OUT-METHOD",httpCmd.method); }

	fetch(url,httpCmd).then(response => {
		if (debugAPI) console.log("API>>> Resp",response);

		if (response.status != okResp) {
			response.text().then(
				data => {
					if (debugAPI) console.log("API>>> BAD",response.status,response.statusText);
					if (response.status != 499) return we_are_done(false,{"error":"Unexecpted System Error"});
					check_session(response.headers);
					try {
						return we_are_done(false,JSON.parse(data));
					} catch {
						return we_are_done(false,{"error":data});
						}
					},
				() => errMsg(`ERROR:2: ${response.status} ${response.statusText}`)
				);
			return;
			}
		else {
			response.text().then(data => {
				check_session(response.headers);

				if (debugAPI) console.log("API>>> OK",response.status,response.statusText);

				if ((inData != null)&&(inData.noData)) {
					return we_are_done(true,true);
				} else {
					let param = data;
					try {
						param = JSON.parse(data); }
					catch {
						param = data; }

					return we_are_done(true,param);
					}
				});
			}
		})
		.catch((err) => {
			we_are_done(false,{"error":"Server connection error"})
			} );
}



function policy(name,val)
{
	if (!("config" in gbl)) return val;
	if (!("policy" in gbl.config)) return val;
	if (!(name in gbl.config.policy)) return val;
	return gbl.config.policy[name];
}



function fromPuny(fqdn)
{
	if ((fqdn.substr(0,4)=="xn--")||(fqdn.indexOf(".xn--") > 0))
		return toUnicode(fqdn);
	return fqdn;
}



function btn(call,txt,hlp,sz)
{
	let ex=""
	if (sz != null) ex = `style='width: ${sz}px;'`
	return `<span ${ex} tabindex=0 title="${hlp}" class=myBtn onClick="${call}; return false;">${txt}</span>`;
}


function supported_tld(fqdn)
{
	if ((pos = fqdn.indexOf(".")) < 0) return false;
	return (fqdn.substr(pos+1) in gbl.config.ok_tlds);
}



function format_amount(num,omit_symbol)
{
	if (num==null) return "";
	let cur = gbl.config.currency;
	let pfx = cur.symbol;
	if (omit_symbol) pfx = "";
	if (num < 0) { pfx += "-"; num *= -1; }
	num = num.toString();
	if (num.length < (cur.decimal+1))
		num = ("000000000000000"+num).slice((cur.decimal+1)*-1);

	let neg_places = -1 * cur.decimal;
	let use_start="";
	let start = num.slice(0,neg_places);
	while(start.length > 3) {
		use_start += cur.separator[0]+start.slice(-3);
		start = start.slice(0,-3);
		}

	if (start.length) use_start = start+use_start;
	return pfx+use_start+cur.separator[1]+num.slice(neg_places);
}




function def_errMsg(msg,reply,tagged_elm)
{
	if ((reply)&&(reply.error)) errMsg(reply.error,tagged_elm); else errMsg(msg,tagged_elm);
}


function unerrMsg()
{
	let t1 = elm.myMsgPop.innerHTML;
	let t2 = ctx.lastErrMsg;
	if (t2 == null) t2 = "";
	if (t1 == t2) elm.myMsgPop.className = "msgPop msgPopNo";
	delete ctx.lastErrMsg;
	if ("err_msg_tout" in ctx) clearTimeout(ctx.err_msg_tout);
	delete ctx.err_msg_tout;
}



function errMsg(txt,tagged_elm)
{
	let hang_elm = null;
	if (tagged_elm in elm) hang_elm = elm[tagged_elm];
	else hang_elm = document.getElementById(tagged_elm);
	if (!hang_elm) hang_elm = elm.userInfo;

	let m = elm.myMsgPop;
	m.style.width = "auto";
	if (txt.slice(0,1)!="&") txt = gbl.warn + " " + txt;
	m.innerHTML = "&nbsp;"+txt+"&nbsp;";

	let p_box = hang_elm.getBoundingClientRect();
	let m_box = m.getBoundingClientRect();
	let m_width = m_box.width;

	if (m_box.width < p_box.width) {
		m.style.width = p_box.width + "px";
		m_width = p_box.width;
		}
	let centre = p_box.x + (p_box.width/2);
	let x_pos = centre - (m_width / 2)
	m.style.left = x_pos + "px";
	m.style.top = p_box.y + p_box.height + "px";

	m.className = 'msgPop msgPopYes';
	ctx.lastErrMsg = m.innerHTML;
	ctx.err_msg_tout = setTimeout(unerrMsg,2500);

	return false;
}



function hasIDN(name)
{
	if (name.slice(0,4)=="xn--") return true;
	if (name.indexOf(".xn--") > 0) return true
	return false;
}



function changeFavicon(src)
{
	var link = document.createElement('link'),
		oldLink = document.getElementById('dynamic-favicon');

	link.id = 'dynamic-favicon';
	link.rel = 'shortcut icon';
	link.href = src;
	if (oldLink) gbl.head.removeChild(oldLink);
	gbl.head.appendChild(link);
}



function clean_host_name(dom_name,hostname)
{
	if (!hostname) return "";
	if (hostname==dom_name) return '@';
	if (hostname.slice(-1*dom_name.length)==dom_name) hostname = hostname.slice(0,-1*(dom_name.length+1))
	if (hasIDN(hostname)) hostname = fromPuny(hostname);
	return hostname;
}



function sort_rr_sets(reply)
{
	reply.dns.rrsets.sort((a,b) => {
		if ((a.name == reply.dns.name)&&(b.name == reply.dns.name)) {
			for(tag of ["SOA","NS","MX"]) {
				if (a.type == tag) return -1;
				if (b.type == tag) return 1;
				}
			}
		else {
			if (a.name == reply.dns.name) return -1;
			if (b.name == reply.dns.name) return 1;
			if (a.name < b.name) return -1;
			if (a.name > b.name) return 1;
			}
		if (a.type < b.type) return -1;
		if (a.type > b.type) return 1;
		return 0;
		})
}



function form_prompt(txt) { return `<tr><td class=formPrompt>${txt} :</td><td>`; }
function settings_prompt(txt) { return `<tr><td class=promptCell>${txt} :</td><td>`; }


function settings_header(title,spacer)
{
    let x = "";
    if (!spacer) x = gbl.settings_spacer;
    x += `<tr><td class=settingsBanner>${title}</td></tr><tr><td>`;
    return x;
}



function generic_popup_btn(config)
{
    /* config: width, style, title, name, label, internal(), param */
    let style_width="",pop_style="";
    if ("width" in config) style_width = `style='width: ${config["width"]}px;'`;
    if ("style" in config) pop_style = `style='${config["style"]}'`;

    let timeout = 30000;
    if ("timeout" in config) timeout = config.timeout;

    let x = `<div class="popup">`;
    x += `<span ${style_width}75px;' tabindex=0 title="${config["title"]}" `;
    x += `class=myBtn onClick="togglePopUp('${config["name"]}',${timeout});">${config["label"]}</span>`;
    x += `<span class="popuptext" ${pop_style} id="${config["name"]}">`;
    x += config["internal"](config["param"]);
    return x + `</span></div>`;
}



function add_payment_script(module) {
    let s = document.createElement('script');
    s.setAttribute("src", "/"+module+".js" );
    s.setAttribute("type", 'text/javascript');
    s.onload = () => { eval(module+"_startup()"); };
    document.body.appendChild( s );
}



function rand_tag(want_char)
{
	if (!want_char) want_char = 30
	let myar = new Uint8Array(10);
    return btoa(window.crypto.getRandomValues(myar)).slice(0,want_char);
}
