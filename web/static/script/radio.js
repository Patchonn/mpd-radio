
function secToTime(seconds) {
    return Math.floor(seconds / 60) + ":" + (seconds % 60).toString().padStart(2, "0");
}

function appendIcon(icon){
    return function(el) {
        el.append("i")
            .toggleClass("icon", true)
            .toggleClass("icon-" + icon, true);
    };
}

class slider {
    constructor(el, cb, def){
        this.element = el;
        this.display = el.firstElementChild;
        this.cb = cb;
        
        if(def && !isNaN(def)) this.setWidth(def);
        
        this.mouse_down = false;
        this.element.addEventListener("mousedown", (ev) => {
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
        let rel = Math.min(Math.max(ev.pageX - this.element.offsetLeft, 0), this.element.offsetWidth);
        let percent = rel / this.element.offsetWidth;
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


class SongElement {
    constructor(container, append){
        this.append = append !== undefined ? append : false;
        this.e_container = container;
        
        if(this.append)
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
        
        // icons
        this.e_icons =
            this.e_container.append("span")
                .toggleClass("pl-icons", true);
    }
    
    update(info){
        if(this.lastInfo === undefined || this.lastInfo.file !== info.file){
            this.lastInfo = info;
            this.e_container.attr("title", info.toString());
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
    remove() {
        if(this.append)
            this.e_container.remove();
    }
    
    addButton(icon, label, callback) {
        this.e_icons
            .append("i")
                .toggleClass("icon", true)
                .toggleClass("icon-" + icon, true)
                .attr("title", label)
                .listen("click", callback.bind(this));
    }
}

class UploadEntry {
    constructor(file, container, retry) {
        this.failed = false;
        this.file = file;
        this.retry = retry;
        
        this.e_element = container.append("div");
        
        let desc = 
            this.e_element
                .toggleClass("upload-entry", true)
                .append("div")
                    .toggleClass("upload-description", true);
        
        desc.append("span")
            .toggleClass("icons-set", true)
            .call(appendIcon("file-upload"))
            .call(appendIcon("exclamation-triangle"))
            .call(appendIcon("upload"))
        
        desc.append("span")
            .toggleClass("upload-filename", true)
            .text(file.name);
            
        this.e_progress = 
            this.e_element
                .append("div")
                    .toggleClass("upload-progress", true)
                    .append("div");
        
        
        this.e_element.listen("click", (e) => {
            if(this.failed) {
                /* // don't need this as we're just gonna remove this entry
                this.failed = false;
                this.e_element.toggleClass("upload-failed", false);
                */
                this.retry(this.file);
                this.remove();
            }
        });
    }
    
    updateProgress(percent) {
        this.e_progress.style("width", percent.toString() + "%");
    }
    
    error() {
        this.failed = true;
        this.e_element.toggleClass("upload-failed", true);
    }
    
    remove() {
        this.e_element.remove();
    }
}

class RadioUploader {
    constructor() {
        this.e_popup = du.id("uploads");
        this.e_prog = du.id("progress-container");
        this.e_queued = du.id("upload-queued");
        
        this.e_list = du.query("#uploaded .pl-list");
        
        this.upload = scheduler(this.upload.bind(this), radio.config.CONCURRENT_UPLOADS);
        this.queued = 0;
        
        this.e_popup.toggleClass("hide", false);
        
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
            for(let i = 0; i < files.length; i++)
                this.enqueue(files[i]);
        });
    }
    
    updateQueued() {
        this.e_queued.text("queued files: " + this.queued);
        if(this.queued > 0) {
            this.e_queued.toggleClass("hide", false);
        } else {
            this.e_queued.toggleClass("hide", true);
        }
    }
    enqueue(file) {
        this.queued++;
        this.updateQueued();
        
        this.upload(file);
    }
    dequeue() {
        this.queued--;
        this.updateQueued();
    }
    
    async upload(file) {
        this.dequeue();
        
        let entry = new UploadEntry(file, this.e_prog, this.upload);
        
        let response = radio.upload(file, entry.updateProgress.bind(entry));
        
        let success = false;
        let info;
        try {
            info = await response;
            success = true;
        } catch(e) {
            if(e.status !== undefined && e.status == 409)
                entry.remove();
            else
                entry.error();
            console.log(e);
        }
        
        if(success) {
            entry.remove();
            
            let elem = new SongElement(this.e_list, true);
            elem.update(info);
            
            if(info.token !== undefined) {
                elem.addButton("plus-square", "request", function() {
                    radio.request(info.token);
                    this.remove();
                });
            }
            elem.addButton("times", "remove", function() {
                this.remove();
            });
        }
    }
}

// does this even warrant a class?
class Radio {
    constructor(){
        // this class is a mess
        // change everything to classes
        // separate each ui element into its own class
        // the player should have a class
        // each list should have a class as well
        // the uploader can keep its class but needs a few changes
        this.e_audio = du.id("stream-player");
        
        this.e_elapsed = du.id("time-elapsed");
        this.e_length = du.id("time-length");
        this.e_progress = du.id("progress-bar");
        
        this.e_play = du.id("play-btn");
        this.e_pause = du.id("pause-btn");
        this.e_mute = du.id("mute-btn");
        this.e_unmute = du.id("unmute-btn");
        
        this.e_currentSong = du.id("now-playing");
        this.e_recent = du.id("recent");
        this.e_queue = du.id("queue");
        
        this.currentSong = new SongElement(this.e_currentSong);
        
        this.recent = [];
        this.queue = [];
        
        let vol = parseFloat(localStorage.getItem("volume"));
        if(!isNaN(vol)) this.e_audio.element.volume = vol;
        new slider(document.getElementById("volume"), (vol) => {
            this.e_audio.element.volume = vol;
            localStorage.setItem("volume", vol);
        }, vol);
        
        let muted = localStorage.getItem("muted") === "true";
        if(muted) this.mute();
        
        this.e_play.listen("click", this.play.bind(this));
        this.e_pause.listen("click", this.pause.bind(this));
        
        this.e_mute.listen("click", this.mute.bind(this));
        this.e_unmute.listen("click", this.unmute.bind(this));
        
        this.updateInterval = radio.config.UPDATE_INTERVAL;
        if(radio.config.UPLOADS_ENABLED === true)
            this.uploader = new RadioUploader();
        
        document.title = radio.config.WEBSITE_TITLE;
        
        this.start();
    }
    
    async start(){
        await this.updateInfo();
        this.infoInterval = setInterval(this.updateInfo.bind(this), this.updateInterval);
        this.updateProgress();
    }
    
    play(){
        this.e_audio.element.firstElementChild.src = radio.config.AUDIO_SOURCE + "?nocache=" + Date.now();
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
    
    async updateInfo(){
        let old = this.info;
        this.info = await radio.info();
        
        let currentInfo = this.info.playlist[parseInt(this.info.status.song)];
        let oldInfo = !!old && old.playlist[parseInt(old.status.song)];
        this.elapsed = Math.floor(parseFloat(this.info.status.elapsed) * 1000);
        this.lastTime = Date.now();
        if(!old || currentInfo.file != oldInfo.file) {
            this.currentInfo = currentInfo;
            
            // update document title
            document.title = this.currentInfo.toString(false).replace(/\n/g, " - ") + " | " + radio.config.WEBSITE_TITLE;
            
            // update player info
            this.e_length.text(this.currentInfo.timeStr);
            
            // update current track info
            this.currentSong.update(this.currentInfo);
            
            // update playlists
            let song = parseInt(this.info.status.song);
            let recent = this.info.playlist.slice(0, song).reverse();
            let queue = this.info.playlist.slice(song + 1);
            this.updatePlaylist(this.e_recent, this.recent, recent);
            this.updatePlaylist(this.e_queue, this.queue, queue);
            
        } else if(!!old && old.playlist.length != this.info.playlist.length) {
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
        
        let total = this.currentInfo.time;
        this.elapsed += diff;
        let elapsedSec = secToTime(Math.floor(this.elapsed / 1000));
        this.e_elapsed.text(elapsedSec);
        this.e_progress.style("width", ((this.elapsed / 10) / total) + "%");
        
        if(this.elapsed > (total + 1) * 1000){
            console.log(this.elapsed);
            console.log(total);
            this.updateInfo();
        }
        
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
        
        let diff = list.length - elements.length;
        
        // create missing children
        for(let i = 0; i < diff; i++){
            elements.push(new SongElement(elem, true));
        }
        
        // hide extra children
        for(let i = 0; i < -diff; i++){
            // could just always hide everything
            let entry = elements[elements.length - 1 - i];
            entry.hide();
        }
        
        for(let i = 0; i < list.length; i++){
            let info = list[i];
            let entry = elements[i];
            
            entry.show();
            entry.update(info);
        }
    }
}

window.addEventListener("load", async function(){
    await radio.loadConfig();
    
    let links = du.id("stream-links");
    for(let i = 0; i < radio.config.EXTRA_LINKS.length; i++) {
        let entry = radio.config.EXTRA_LINKS[i];
        let link = 
            links.append("a")
                .attr("href", entry[1])
                .text(entry[0]);
        
        if(entry[2]) link.attr("target", "_blank");
        if(entry[3]) link.attr("download", true);
    }
    
    radio.mgr = new Radio();
    
});
