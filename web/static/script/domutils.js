
// dom utils
window.du = window.du || {};

(function(du){
    
    class Element {
        constructor(element, parent) {
            this.parent_ = (parent !== undefined) ? parent : null;
            
            this.element = element;
            this.doc = element.ownerDocument;
        }
        
        attr(name, value) {
            if(value === null)
                this.element.removeAttribute(name);
            else
                this.element.setAttribute(name, value);
            
            return this;
        }
        data(name, value) {
            if(value === null)
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
        
        parent() {
            return this.parent_;
        }
        
        append(tag){
            let child = this.doc.createElement(tag);
            this.element.appendChild(child);
            return new Element(child, this);
        }
        appendChild(tag){
            let child = this.doc.createElement(tag);
            this.element.appendChild(child);
            return this;
        }
        remove() {
            this.element.parentNode.removeChild(this.element);
        }
        
        call(fun) {
            fun(this);
            return this;
        }
        
        select(query) {
            let selection = this.element.querySelector(query);
            if(selection === null) return null;
            return new Element(selection);
        }
    };
    
    du.select = function(query, doc) {
        doc = (doc !== undefined) ? doc : document;
        if(query.nodeType > 0) {
            return new Element(query);
        } else {
            let selection = doc.querySelector(query);
            if(selection === null) return null;
            return new Element(selection);
        }
    };
    du.query = du.select;
    du.id = function(id, doc) {
        doc = (doc !== undefined) ? doc : document;
        let element = doc.getElementById(id);
        if(element === null) return null;
        return new Element(element);
    };
    
})(window.du);

