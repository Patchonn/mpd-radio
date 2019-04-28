
async function loadConfig(url) {
    let xhr = new XMLHttpRequest();
    xhr.responseType = "json";
    
    return new Promise(function(resolve, reject){
        xhr.addEventListener("load", function(e){
            if(xhr.readyState == 4){
                resolve(xhr.response);
            }
        }, false);
        xhr.addEventListener("error", function(e){
            reject(Error(e));
        }, false);
        
        xhr.open("GET", url, true);
        xhr.send();
    });
}
