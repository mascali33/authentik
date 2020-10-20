import { LitElement, html } from 'lit-element';
import { updateMessages } from "./Messages.js";

class FetchFillSlot extends LitElement {

    static get properties() {
        return {
            flowBodyUrl: { type: String },
            flowBody: { type: String },
        };
    }

    createRenderRoot() {
        return this;
    }

    firstUpdated() {
        fetch(this.flowBodyUrl).then(r => r.json()).then(r => this.updateCard(r));
    }

    async updateCard(data) {
        switch (data.type) {
            case "redirect":
                window.location = data.to
                break;
            case "template":
                this.flowBody = data.body;
                await this.requestUpdate();
                this.checkAutofocus();
                updateMessages();
                this.loadFormCode();
                this.setFormSubmitHandlers();
            default:
                break;
        }
    };

    loadFormCode() {
        this.querySelectorAll("script").forEach(script => {
            let newScript = document.createElement("script");
            newScript.src = script.src;
            document.head.appendChild(newScript);
        });
    }

    checkAutofocus() {
        const autofocusElement = this.querySelector("[autofocus]");
        if (autofocusElement !== null) {
            autofocusElement.focus();
        }
    }

    updateFormAction(form) {
        for (let index = 0; index < form.elements.length; index++) {
            const element = form.elements[index];
            if (element.value === form.action) {
                console.log("pb-flow: Found Form action URL in form elements, not changing form action.");
                return false;
            }
        }
        form.action = this.flowBodyUrl;
        console.log(`pb-flow: updated form.action ${this.flowBodyUrl}`);
        return true;
    }

    checkAutosubmit(form) {
        if ("autosubmit" in form.attributes) {
            return form.submit();
        }
    }

    setFormSubmitHandlers() {
        this.querySelectorAll("form").forEach(form => {
            console.log(`pb-flow: Checking for autosubmit attribute ${form}`);
            this.checkAutosubmit(form);
            console.log(`pb-flow: Setting action for form ${form}`);
            this.updateFormAction(form);
            console.log(`pb-flow: Adding handler for form ${form}`);
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                let formData = new FormData(form);
                this.flowBody = undefined;
                fetch(this.flowBodyUrl, {
                    method: 'post',
                    body: formData,
                }).then(response => response.json()).then(data => {
                    this.updateCard(data);
                });
            });
            form.classList.add("pb-flow-wrapped");
        });
    }

    loading() {
        return html`
            <div class="pf-c-login__main-body pb-loading">
                <span class="pf-c-spinner" role="progressbar" aria-valuetext="Loading...">
                    <span class="pf-c-spinner__clipper"></span>
                    <span class="pf-c-spinner__lead-ball"></span>
                    <span class="pf-c-spinner__tail-ball"></span>
                </span>
            </div>`;
    }

    render() {
        if (this.flowBody !== undefined) {
            return html([this.flowBody]);
        }
        return this.loading();
    }
}

customElements.define('flow-shell-card', FetchFillSlot);