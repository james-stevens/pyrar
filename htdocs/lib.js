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
        .catch(err => errMsg(`ERROR:3: Failed to connect to server (${err})`))

    document.body.style.cursor="auto";
}
