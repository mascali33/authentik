import { CSSResult, customElement, html, LitElement, property, TemplateResult } from "lit-element";
import { AKPagination } from "../../api/Client";
import { t } from "@lingui/macro";
import PFBase from "@patternfly/patternfly/patternfly-base.css";
import PFButton from "@patternfly/patternfly/components/Button/button.css";
import PFPagination from "@patternfly/patternfly/components/Pagination/pagination.css";
import AKGlobal from "../../authentik.css";

@customElement("ak-table-pagination")
export class TablePagination extends LitElement {
    @property({ attribute: false })
    pages?: AKPagination;

    @property({ attribute: false })
    // eslint-disable-next-line
    pageChangeHandler: (page: number) => void = (page: number) => {};

    static get styles(): CSSResult[] {
        return [PFBase, PFButton, PFPagination, AKGlobal];
    }

    render(): TemplateResult {
        return html` <div class="pf-c-pagination pf-m-compact pf-m-hidden pf-m-visible-on-md">
            <div class="pf-c-pagination pf-m-compact pf-m-compact pf-m-hidden pf-m-visible-on-md">
                <div class="pf-c-options-menu">
                    <div class="pf-c-options-menu__toggle pf-m-text pf-m-plain">
                        <span class="pf-c-options-menu__toggle-text">
                            ${t`${this.pages?.startIndex} - ${this.pages?.endIndex} of ${this.pages?.count}`}
                        </span>
                    </div>
                </div>
                <nav class="pf-c-pagination__nav" aria-label="Pagination">
                    <div class="pf-c-pagination__nav-control pf-m-prev">
                        <button
                            class="pf-c-button pf-m-plain"
                            @click=${() => {
                                this.pageChangeHandler(this.pages?.previous || 0);
                            }}
                            ?disabled="${(this.pages?.previous || 0) < 1}"
                            aria-label="${t`Go to previous page`}"
                        >
                            <i class="fas fa-angle-left" aria-hidden="true"></i>
                        </button>
                    </div>
                    <div class="pf-c-pagination__nav-control pf-m-next">
                        <button
                            class="pf-c-button pf-m-plain"
                            @click=${() => {
                                this.pageChangeHandler(this.pages?.next || 0);
                            }}
                            ?disabled="${(this.pages?.next || 0) <= 0}"
                            aria-label="${t`Go to next page`}"
                        >
                            <i class="fas fa-angle-right" aria-hidden="true"></i>
                        </button>
                    </div>
                </nav>
            </div>
        </div>`;
    }
}
