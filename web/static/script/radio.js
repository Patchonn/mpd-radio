
const CONFIG_URL = "/api/config.json";

// failsafe because javascript is amazing
const UPDATE_INTERVAL = 10 * 1000;

function secToTime(seconds) {
    return Math.floor(seconds / 60) + ":" + (seconds % 60).toString().padStart(2, "0");
}

class slider {
    constructor(el, cb, def){
        this.parent = el;
        this.display = el.firstElementChild;
        this.cb = cb;
        
        if(def) this.setWidth(def);
        
        this.mouse_down = false;
        this.parent.addEventListener("mousedown", (ev) => {
            ev.preventDefault();
            console.log(ev);
            if(ev.button == 0){
                this.mouse_down = true;
                this.change(ev);
            }
        });
        document.addEventListener("mouseup", (ev) => {
            this.mouse_down = false;
        });
        document.addEventListener("mousemove", (ev) => {
            if(this.mouse_down){
                ev.preventDefault();
                this.change(ev);
            }
        });
    }
    
    change(ev) {
        let rel = Math.min(Math.max(ev.pageX - this.parent.offsetLeft, 0), this.parent.offsetWidth);
        let percent = rel / this.parent.offsetWidth;
        this.setWidth(percent);
        this.cb(percent);
    }
    
    setWidth(percent){
        this.display.style.width = (percent * 100) + "%";
    }
}

function scheduler(task, concurrent){
    let resolvers = [];
    let promises = [];
    
    function add_task(){
        promises.push(new Promise(resolve => {
            resolvers.push(resolve);
        }));
    }
    
    function replace_task(){
        if(!resolvers.length)
            add_task();
        
        resolvers.shift()();
    }
    
    function get_task(){
        if(!promises.length)
            add_task();
        
        return promises.shift();
    }
    
    for(let i = 0; i < concurrent; i++){
        add_task();
        resolvers.shift()();
    }
    
    return async (...args) => {
        await get_task();
        try{
            await task(...args);
        }catch(e){
            console.error(e);
        }
        replace_task();
    };
}

// replace with a function that takes a drop area element and returns the scheduled upload function
class RadioUploader {
    constructor(){
        this.e_popup = du.id("upload");
        this.e_dialog = du.id("upload-dialog");
        this.e_prog = du.id("progress-container");
        this.e_queued = du.id("upload-queued");
        
        this.upload = scheduler(this.upload.bind(this), config.CONCURRENT_UPLOADS);
        this.queued = 0;
        
        document.body.addEventListener("dragenter", (e) => {
            e.stopPropagation();
            e.preventDefault();
            this.e_popup.toggleClass("file_hover", true);
        });
        
        document.body.addEventListener("dragleave", (e) => {
            e.stopPropagation();
            e.preventDefault();
            this.e_popup.toggleClass("file_hover", false);
        });
        
        document.body.addEventListener("dragover", (e) => {
            e.stopPropagation();
            e.preventDefault();
            e.dataTransfer.dropEffect = "copy";
            this.e_popup.toggleClass("file_hover", true);
        });
        
        document.body.addEventListener("drop", (e) => {
            e.stopPropagation();
            e.preventDefault();
            this.e_popup.toggleClass("file_hover", false);
            this.e_popup.toggleClass("loading", true);
            
            let files = e.target.files || e.dataTransfer.files;
            for(let i = 0; i < files.length; i++){
                this.queued++;
                this.upload(files[i]);
            }
        });
    }
    
    async upload(file){
        this.queued--;
        
        let e_progress;
        
        let e_entry = this.e_prog.append("div")
            .toggleClass("upload-entry", true)
            .append("div")
                .toggleClass("upload-filename", true)
                .text(file.name)
            .parent()
            
            .append("div")
                .toggleClass("upload-progress", true)
                .append("div")
                    .call((e) => {e_progress = e;})
                .parent()
            .parent();
        
        /*
        if(file.size > 500000000)
            return;
        */
        
        let form = new FormData();
        form.append("file", file);
        
        let xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener("progress", function(e){
            let percent = 0;
            if(e.lengthComputable)
                percent = Math.floor((e.loaded / e.total) * 100);
            else
                percent = 100;
            
            e_progress.style("width", percent.toString() + "%");
        });
        
        let result = new Promise(function(resolve, reject){
            xhr.addEventListener("load", function(e){
                if(xhr.readyState == 4){
                    resolve(xhr);
                }
            }, false);
            xhr.addEventListener("error", function(e){
                reject(Error(e));
            }, false);
        });
        
        xhr.open("POST", config.API_ENDPOINT + "/api/upload", true);
        xhr.send(form);
        
        await result;
        console.log(xhr.response);
        
        e_entry.remove();
    }
    
    set queued(val){
        this.qd = val;
        this.e_queued.text("queued files: " + this.qd);
        if(this.qd){
            this.e_queued.toggleClass("hide", false);
            this.e_dialog.toggleClass("hide", true);
        }else{
            this.e_queued.toggleClass("hide", true);
            this.e_dialog.toggleClass("hide", false);
        }
    }
    get queued(){
        return this.qd;
    }
}

class SongInfo {
    constructor(info){
        this.info = info
        this.file = info.file;
        this.filename = info.file.substr(info.file.indexOf("/") + 1);
        this.url = config.API_ENDPOINT + "/music/" + this.filename;
        
        this.title = info.title ? info.title : this.filename;
        this.artist = info.artist ? info.artist : "unknown artist";
        this.album = info.album ? info.album : null; //"unknown album";
        
        this.thumb = config.API_ENDPOINT + info.thumb;
        
        this.time = parseInt(info.time);
        this.timeStr = secToTime(parseInt(info.time));
    }
}

class SongElement {
    constructor(container, append){
        append = append !== undefined ? append : false;
        this.e_container = container;
        
        if(append)
            this.e_container = this.e_container.append("div");
        
        /*
        <a class="pl-art"><img src=""/></a>
        <div class="pl-info">
            <a href="#" class="pl-title" download></a>
            <span class="pl-artist"></span>
            <span class="pl-album"></span>
            <span class="pl-time"></span>
        </div>
        */
        this.e_container.toggleClass("pl-row", true);
        
        this.e_artAnchor = 
            this.e_container.append("a")
                .attr("href", "#")
                .attr("download", "")
                .toggleClass("pl-art", true);
        
        this.e_art =
            this.e_artAnchor.append("img")
                .listen("load", (e, el) => {el.toggleClass("hide", false)})
                .listen("error", (e, el) => {el.toggleClass("hide", true)});
        
        let e_info = this.e_container.append("div").toggleClass("pl-info", true);
        
        this.e_title =
            e_info.append("a")
                .toggleClass("pl-title", true)
                .attr("href", "#")
                .attr("download", "");
        
        this.e_artist =
            e_info.append("span")
                .toggleClass("pl-artist", true);
        
        this.e_album =
            e_info.append("span")
                .toggleClass("pl-album", true);
        
        this.e_time =
            e_info.append("span")
                .toggleClass("pl-time", true);
    }
    
    update(info){
        if(this.lastInfo === undefined || this.lastInfo.file !== info.file){
            this.lastInfo = info;
            this.e_artAnchor.attr("href", info.url);
            this.e_art.attr("src", info.thumb);
            this.e_title.text(info.title).attr("href", info.url);
            this.e_artist.text(info.artist);
            this.e_album.text(info.album);
            this.e_album.toggleClass("hide", info.album === null);
            this.e_time.text(info.timeStr);
        }
    }
    
    show() {
        this.e_container.toggleClass("hide", false);
    }
    hide() {
        this.e_container.toggleClass("hide", true);
    }
}

// does this even warrant a class?
class Radio {
    constructor(){
        this.e_audio = du.id("stream-player");
        
        this.e_elapsed = du.id("time-elapsed");
        this.e_length = du.id("time-length");
        this.e_progress = du.id("progress-bar");
        
        this.e_currentSong = du.id("now-playing");
        this.currentSong = new SongElement(this.e_currentSong);
        
        this.e_recent = du.id("recent");
        this.e_queue = du.id("queue");
        this.recent = [];
        this.queue = [];
        
        this.e_play = du.id("play-btn");
        this.e_pause = du.id("pause-btn");
        
        this.e_mute = du.id("mute-btn");
        this.e_unmute = du.id("unmute-btn");
        
        this.recent = [];
        this.queue = [];
        
        let vol = localStorage.getItem("volume");
        if(vol) this.e_audio.element.volume = parseFloat(vol);
        new slider(document.getElementById("volume"), (vol) => {
            this.e_audio.element.volume = vol;
            localStorage.setItem("volume", vol);
        }, vol);
        
        let muted = localStorage.getItem("muted");
        if(muted) this.mute();
        
        this.e_play.listen("click", this.play.bind(this));
        this.e_pause.listen("click", this.pause.bind(this));
        
        this.e_mute.listen("click", this.mute.bind(this));
        this.e_unmute.listen("click", this.unmute.bind(this));
        
        this.updateInterval = config.UPDATE_INTERVAL;
        this.uploader = new RadioUploader();
        
        this.start();
    }
    
    async start(){
        await this.updateInfo();
        this.infoInterval = setInterval(this.updateInfo.bind(this), this.updateInterval);
        this.updateProgress();
    }
    
    play(){
        this.e_audio.element.firstElementChild.src = config.AUDIO_SOURCE + "?nocache=" + Date.now();
        this.e_audio.element.load();
        this.e_audio.element.play();
        this.e_play.toggleClass("hide", true);
        this.e_pause.toggleClass("hide", false);
    }
    pause(){
        this.e_audio.element.pause();
        this.e_audio.element.currentTime = 0;
        this.e_audio.element.firstElementChild.src = "";
        this.e_play.toggleClass("hide", false);
        this.e_pause.toggleClass("hide", true);
    }
    
    mute(){
        this.e_audio.element.muted = true;
        localStorage.setItem("muted", true);
        this.e_mute.toggleClass("hide", true);
        this.e_unmute.toggleClass("hide", false);
    }
    unmute(){
        this.e_audio.element.muted = false;
        localStorage.setItem("muted", false);
        this.e_mute.toggleClass("hide", false);
        this.e_unmute.toggleClass("hide", true);
    }
    
    // info, list, add
    makeRequest(httpMethod, method, params){
        return new Promise((resolve, reject) => {
            let xhr = new XMLHttpRequest();
            xhr.addEventListener("load", function(){
                if(xhr.readyState == 4){
                    if(this.status != 200)
                        reject(new Error("api error: " + this.responseText));
                    
                    resolve(JSON.parse(this.responseText));
                }
            });
            xhr.addEventListener("error", function(e){
                reject(new Error("xhr error"));
            });
            xhr.open(httpMethod, config.API_ENDPOINT + "/api/" + method);
            xhr.send(null);
        });
    }
    async getInfo(){
        return await this.makeRequest("GET", "info");
    }
    
    async updateInfo(){
        let old = this.info;
        this.info = await this.getInfo();
        
        let curInfo = this.info.playlist[parseInt(this.info.status.song)];
        this.elapsed = Math.floor(parseFloat(this.info.status.elapsed) * 1000);
        this.lastTime = Date.now();
        if(!old || old.playlist[parseInt(old.status.song)].file != curInfo.file){
            this.currentinfo = new SongInfo(curInfo);
            
            // update player info
            this.e_length.text(this.currentinfo.timeStr);
            
            // update current track info
            this.currentSong.update(this.currentinfo);
            
            // update playlists
            let song = parseInt(this.info.status.song);
            let recent = this.info.playlist.slice(0, song).reverse();
            let queue = this.info.playlist.slice(song + 1);
            this.updatePlaylist(this.e_recent, this.recent, recent);
            this.updatePlaylist(this.e_queue, this.queue, queue);
        }
    }
    updateProgress(){
        let diff = Date.now() - this.lastTime;
        this.lastTime = Date.now();
        
        let total = this.currentinfo.time;
        this.elapsed += diff;
        let elapsedSec = secToTime(Math.floor(this.elapsed / 1000));
        this.e_elapsed.text(elapsedSec);
        this.e_progress.style("width", ((this.elapsed / 10) / total) + "%");
        
        requestAnimationFrame(this.updateProgress.bind(this));
    }
    
    updatePlaylist(playlist, elements, list){
        let elem = playlist.select(".pl-list");
        let empty = playlist.select(".pl-none");
        
        if(list.length == 0){
            elem.toggleClass("hide", true);
            empty.toggleClass("hide", false);
        }else{
            elem.toggleClass("hide", false);
            empty.toggleClass("hide", true);
        }
        
        // compare to this.recent and this.queue
        // keep track of the 
        let diff = list.length - elements.length;
        
        // create missing children
        for(let i = 0; i < diff; i++){
            elements.push(new SongElement(elem, true));
        }
        
        // hide extra children
        for(let i = 0; i > diff; i--){
            let entry = elements[i];
            entry.hide();
        }
        
        for(let i = 0; i < list.length; i++){
            let info = new SongInfo(list[i]);
            let entry = elements[i];
            
            entry.show();
            entry.update(info);
        }
    }
}

window.addEventListener("load", async function(){
    window.config = await loadConfig(CONFIG_URL);
    
    document.title = config.WEBSITE_TITLE;
    
    let links = du.id("stream-links");
    for(let i = 0; i < config.EXTRA_LINKS.length; i++) {
        let entry = config.EXTRA_LINKS[i];
        let link = 
            links.append("a")
                .attr("href", entry[1])
                .text(entry[0]);
        
        if(entry[2]) link.attr("target", "_blank");
        if(entry[3]) link.attr("download", true);
    }
    
    if(config.UPDATE_INTERVAL === undefined || config.UPDATE_INTERVAL < UPDATE_INTERVAL)
        config.UPDATE_INTERVAL = UPDATE_INTERVAL;
    
    window.radio = new Radio();
});

