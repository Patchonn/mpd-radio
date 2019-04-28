
class Builder {
    constructor(tag, doc, parent) {
        this.doc = doc !== undefined ? doc : document;
        this.parentBuilder = parent !== undefined ? parent : null;
        
        if(tag.nodeType > 0) {
            this.element = tag;
            this.document = tag.ownerDocument;
        } else {
            this.element = this.doc.createElement(tag);
        }
    }
    
    attr(name, value) {
        if(value === undefined || value === null)
            this.element.removeAttribute(name);
        else
            this.element.setAttribute(name, value);
        
        return this;
    }
    data(name, value) {
        if(value === undefined || value === null)
            delete this.element.dataset[name]
        else
            this.element.dataset[name] = value;
        
        return this;
    }
    style(name, value) {
        name = name.replace(/-(.)/g, (e) => e[1].toUpperCase())
        this.element.style[name] = value;
        return this;
    }
    toggleClass(name, add) {
        this.element.classList.toggle(name, add);
        return this;
    }
    text(txt) {
        this.element.textContent = txt;
        return this;
    }
    listen(name, fun) {
        this.element.addEventListener(name, (e) => {
            return fun.call(this, e, this);
        });
        return this;
    }
    
    append(tag){
        let child = new Builder(tag, this.doc, this);
        this.element.appendChild(child.node());
        return child;
    }
    appendChild(tag){
        let child = new Builder(tag, this.doc, this);
        this.element.appendChild(child.node());
        return this;
    }
    
    node() {
        return this.element;
    }
    parent() {
        return this.parentBuilder;
    }
    call(fun) {
        fun(this);
        return this;
    }
    remove() {
        this.element.parentNode.removeChild(this.element);
    }
}

