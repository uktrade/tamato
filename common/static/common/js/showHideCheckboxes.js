let showMoreClicked = {};

const nodeListForEach = (nodes, callback) => {
    if (window.NodeList.prototype.forEach) {
      return nodes.forEach(callback)
    }
    for (let i = 0; i < nodes.length; i++) {
      callback.call(window, nodes[i], i, nodes)
    }
}

class FilterShowMore {
    constructor(module) {
        this.module = module;
        this.button = this.module.getElementsByClassName('js-filter-show-more')[0];
    }
    init() {
        if (!this.module || !this.button) {
            return
        }
    
        if (this.hasBeenRevealed()) {
            this.revealChoices();
        } else {
            this.button.classList.remove('js-hidden');
            this.button.addEventListener('click', () => this.revealChoices());
        }
    }
    hasBeenRevealed() {
        return showMoreClicked[this.module.getAttribute('data-show-more-id')] !== undefined;
    }
    revealChoices() {
        this.button.classList.add('js-hidden');

        let choices = Array.from(this.module.getElementsByClassName('govuk-checkboxes__item js-hidden'));
        choices.forEach((choice) => {
            choice.style.display = 'block';
        });
        showMoreClicked[this.module.getAttribute('data-show-more-id')] = true;
    }
}

const createShowButton = () => {
    const button = document.createElement('button');
    button.classList.add('govuk-button', 'govuk-button--secondary', 'js-filter-show-more');
    button.innerText = 'Show more';
    button.type = 'button'
    return button;
}

const setupCheckBoxes = () => {
    const checkboxSets = Array.from(document.getElementsByClassName('govuk-checkboxes'));
    checkboxSets.forEach((checkboxSet) => {
        if (checkboxSet.children.length > 10) {
            Array.from(checkboxSet.children).forEach((checkbox, index) => {
                if (index > 9) {
                    checkbox.classList.add('js-hidden')
                }
            })
            checkboxSet.dataset.module="filter-show-more";
            checkboxSet.append(createShowButton());
        }
    })
}

const installFilterShowMore = () => {
    setupCheckBoxes();
    let modules = document.querySelectorAll('[data-module="filter-show-more"]');
    nodeListForEach(modules, (module) => {
        new FilterShowMore(module).init()
    });
}

export default installFilterShowMore;