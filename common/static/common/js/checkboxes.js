
class CheckBoxes {
    PARENT_CHECKBOX = "[data-check-all]";
    url = "/ajax/update-measure-selections/"

    constructor() {
        // initial state set server side from session
        this.state = {};
        // CHECKBOX_NAMES and MULTIPLE_MEASURE_SELECTIONS are set in the template includes/measures/list.jinja
        CHECKBOX_NAMES.forEach(name => {
            this.state[name] = 0;
        })
        MULTIPLE_MEASURE_SELECTIONS.forEach(selection => {
            this.state[selection] = 1;
        })
        this.initCheckboxes();
        this.addEventListeners();
        this.addParentCheckboxEventListener();
    }

    addParentCheckboxEventListener() {
        const parentCheckbox = document.querySelector(this.PARENT_CHECKBOX)
        parentCheckbox.onchange = this.toggleCheckAll.bind(this);
    }

    updateSession() {
        const data = { csrfmiddlewaretoken: CSRF_TOKEN, ...this.state };
        fetch(this.url, {
            method: "POST",
            headers: { "X-CSRFToken": CSRF_TOKEN, "Content-Type": "application/json" },
            body: JSON.stringify(data),
        })
    }

    toggleCheckAll(event) {
        const checkboxSelector = event.target.dataset.checkAll;
        const checkedState = event.target.checked;
        for (let checkbox of document.querySelectorAll('[' + checkboxSelector + ']')) {
            checkbox.checked = checkedState;
            this.state[checkbox.name] = checkedState;
        }
        this.updateSession();
    }

    toggleCheckbox(event) {
        if (event.target.checked) {
            this.state[event.target.name] = 1;
        } else {
            this.state[event.target.name] = 0;
        }
        this.updateSession();
    }

    initCheckboxes() {
        for (let name of Object.keys(this.state)) {
            const element = document.querySelector(`input[type=checkbox][name=${name}]`);
            // there may be checkbox names in the session from other pages
            if (element) {
                element.checked = Boolean(this.state[name]);
            }
        }
    }

    addEventListeners() {
        for (let checkbox of document.querySelectorAll('[data-check-trackedmodel]')) {
            checkbox.onchange = this.toggleCheckbox.bind(this);
        }
    }
}

const initCheckboxes = () => {
    new CheckBoxes();
}

export default initCheckboxes;