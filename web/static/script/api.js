
const CONFIG_URL = "/api/config.json";

// failsafe because javascript is amazing
const UPDATE_INTERVAL = 10 * 1000;

window.radio = window.radio || {};

(function(radio) {
    
    class APIError extends Error {
        constructor(status, message) {
            super(message);
            this.status = status;
        }
    }
    
    class SongInfo {
        constructor(info) {
            this.info = info;
            this.file = info.file;
            this.token = info.token;
            this.filename = info.file.substr(info.file.lastIndexOf("/") + 1);
            this.url = radio.config.API_ENDPOINT + "/music/" + this.filename;
            
            this.title = info.title ? info.title : this.filename;
            this.artist = info.artist ? info.artist : "unknown artist";
            this.album = info.album ? info.album : null; //"unknown album";
            
            this.tracknumber = parseInt(info.track);
            if(isNaN(this.tracknumber)) this.tracknumber = null;
            
            this.thumb = radio.config.API_ENDPOINT + info.thumb;
            
            this.time = parseInt(info.time);
            this.timeStr = secToTime(parseInt(info.time));
        }
        toString(includeTime) {
            includeTime = includeTime !== undefined ? includeTime : true;
            
            let str = '';
            
            if(!this.info.title)
                return this.filename;
            
            //if(this.tracknumber) str += this.tracknumber.toString().padStart(2, "0") + " ";
            str += this.title;
            if(this.artist) str += "\n" + this.artist;
            if(this.album) str += "\n" + this.album;
            if(includeTime) str += "\n" + this.timeStr;
            
            return str;
        }
    }
    radio.SongInfo = SongInfo;
    
    radio.updateConfig = function(conf) {
        if(conf.UPDATE_INTERVAL === undefined || conf.UPDATE_INTERVAL < UPDATE_INTERVAL)
            conf.UPDATE_INTERVAL = UPDATE_INTERVAL;
        
        radio.config = conf;
    };
    radio.loadConfig = function() {
        let xhr = new XMLHttpRequest();
        xhr.responseType = "json";
        
        return new Promise(function(resolve, reject) {
            xhr.addEventListener("load", function(e) {
                if(xhr.readyState == 4) {
                    radio.updateConfig(xhr.response);
                    resolve(xhr.response);
                }
            }, false);
            xhr.addEventListener("error", function(e) {
                reject(new Error(e));
            }, false);
            
            xhr.open("GET", CONFIG_URL, true);
            xhr.send();
        });
    };
    
    function makeRequest(httpMethod, method, params) {
        let url = radio.config.API_ENDPOINT + "/api/" + method;
        if(typeof params === "string") url += "/" + params;
        
        return new Promise((resolve, reject) => {
            let xhr = new XMLHttpRequest();
            xhr.addEventListener("load", function() {
                if(xhr.readyState == 4) {
                    if(this.status != 200)
                        reject(new APIError(this.status, this.responseText.toString()));
                    
                    resolve(JSON.parse(this.responseText));
                }
            });
            xhr.addEventListener("error", function(e) {
                reject(new Error("xhr error: " + method));
            });
            xhr.open(httpMethod, url);
            xhr.send(null);
        });
    }
    
    radio.info = async function() {
        let info = await makeRequest("GET", "info");
        for(let i = 0; i < info.playlist.length; i++) {
            info.playlist[i] = new SongInfo(info.playlist[i]);
        }
        return info;
    }
    
    radio.request = function(token) {
        return makeRequest("GET", "request", token);
    }
    
    radio.upload = function(file, onprogress) {
        let form = new FormData();
        form.append("file", file);
        
        let xhr = new XMLHttpRequest();
        xhr.responseType = "json";
        
        xhr.upload.addEventListener("progress", function(e) {
            let percent = 0;
            if(e.lengthComputable)
                percent = Math.floor((e.loaded / e.total) * 100);
            else
                percent = 100;
            
            onprogress(percent);
        });
        
        let resp = new Promise(function(resolve, reject) {
            xhr.addEventListener("load", function(e) {
                if(xhr.readyState == 4) {
                    if(xhr.status != 200) {
                        reject(new APIError(xhr.status, "upload failed, status code: " + xhr.status));
                        return;
                    }
                    resolve(new SongInfo(xhr.response.song));
                }
            }, false);
            xhr.addEventListener("error", function(e) {
                reject(new Error(e));
            }, false);
        });
        
        xhr.open("POST", radio.config.API_ENDPOINT + "/api/upload", true);
        xhr.send(form);
        
        return resp;
    }
    
})(window.radio);

