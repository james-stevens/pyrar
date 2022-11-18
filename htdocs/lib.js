
// regex for an FQDN hostname
const fqdnCheck = /^(([a-zA-Z0-9_]|[a-zA-Z0-9_][a-zA-Z0-9\-_]*[a-zA-Z0-9_])\.)*(xn--|)[A-Za-z0-9\-]+[.]$/;

// regex for adding a host name
const hostnameCheck = /^([a-zA-Z0-9_*]|[a-zA-Z0-9_][a-zA-Z0-9\-_]*[a-zA-Z0-9_])(\.([a-zA-Z0-9_]|[a-zA-Z0-9_][a-zA-Z0-9\-_]*[a-zA-Z0-9_]))*$/

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


function callApi(sfx,callback,inData)
{
    document.body.style.cursor="progress";

    if (debugAPI) {
        console.log("API>>>",sfx);
        console.log("API>>>",inData);
        }

    let p = "https";
    if (!gbl.with_https) p = "http";
    let url = `${p}://${gbl.server}/api/v1.0/${sfx}`;

    let okResp = 200;
    let httpCmd = { headers: { }, method: 'GET' };

    if (inData != null) {
        if ("method" in inData) httpCmd.method = inData.method;
        if ("json" in inData) {
        	httpCmd.body = JSON.stringify(inData.json);
        	httpCmd.headers["Content-type"] = "application/json";
			httpCmd.method = "POST";
        	}
        if ("okResp" in inData) okResp = inData.okResp;
        }

    fetch(url,httpCmd).then(response => {
        if (debugAPI) console.log("API>>> Resp",response);

        if (response.status != okResp) {
            response.text().then(
                data => {
					if (debugAPI) console.log("API>>> BAD",response.status,response.statusText);
                    try { 
                    	return callback(JSON.parse(data));
					} catch {
                        errMsg(`ERROR:1: ${data} ${response.status} ${response.statusText}`)
                        }
                    },
                () => errMsg(`ERROR:2: ${response.status} ${response.statusText}`)
                );
            return;
            }
		else {
			response.text().then(data => {
				if (debugAPI) console.log("API>>> OK",response.status,response.statusText);
				if ((inData != null)&&(inData.noData)) {
					return callback(true);
				} else {
					let param = data;
					try {
						param = JSON.parse(data); }
					catch {
						param = data; }
					return callback(param);
					}
				});
			}
        })
        .catch(err => callback({"error":"Server connection error"}))

    document.body.style.cursor="auto";
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



function btn(call,txt,hlp,sz) {
    let ex=""
    if (sz != null) ex = `style='width: ${sz}px;'`
    return `<span ${ex} title="${hlp}" class=myBtn onClick="${call}; return false;">${txt}</span>`;
}
