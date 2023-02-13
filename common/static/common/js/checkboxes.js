
class CheckBoxes {
    PARENT_CHECKBOX = "[data-check-all]";
    CHEKCKBOXES = "[data-check-trackedmodel]";
    CHECK_ALL_CHECKBOX = "check-all-checkbox";
    PERSIST_MEASURES_BUTTON = "persist-measure-selections-button";
    url = "/ajax/update-measure-selections/"

    constructor(page) {
        // initial state set server side from session
        this.state = {};
        if (page) { this.page = page; } else this.page = "";

        // get names for checkboxes
        const checkboxes = document.querySelectorAll(this.CHEKCKBOXES);
        checkboxes.forEach(checkbox => {
            this.state[checkbox.name] = 0;
        })

        if (this.page === "measures") {
            // MULTIPLE_MEASURE_SELECTIONS is set in the template includes/measures/list.jinja
            MULTIPLE_MEASURE_SELECTIONS.forEach(selection => {
                this.state[selection] = 1;
            })
            const persistMeasures = document.getElementById(this.PERSIST_MEASURES_BUTTON);
            persistMeasures.remove();
        }

        this.initCheckboxes();
        this.addEventListeners();
        this.addParentCheckboxEventListener();
    }

    addParentCheckboxEventListener() {
        const parentCheckbox = document.querySelector(this.PARENT_CHECKBOX)
        parentCheckbox.onchange = this.toggleCheckAll.bind(this);
    }

    updateSession() {
        if (this.page === "measures") {
            const data = { ...this.state };
            fetch(this.url, {
                method: "POST",
                headers: { "X-CSRFToken": CSRF_TOKEN, "Content-Type": "application/json" },
                body: JSON.stringify(data),
            })
        }
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
        // init check all checkbox
        const container = document.createElement("div");
        container.setAttribute("class", "govuk-form-group");
        const fieldset = document.createElement("fieldset");
        fieldset.setAttribute("class", "govuk-fieldset");
        const container2 = document.createElement("div");
        container2.setAttribute("class", "govuk-checkboxes govuk-checkboxes--small");
        const container3 = document.createElement("div");
        container3.setAttribute("class", "govuk-checkboxes__item");
        const inputElement = document.createElement("input");
        inputElement.setAttribute("class", "govuk-checkboxes__input");
        inputElement.setAttribute("id", "select-all");
        inputElement.setAttribute("name", "select-all");
        inputElement.setAttribute("type", "checkbox");
        inputElement.setAttribute("data-check-all", "data-check-trackedmodel");
        const labelElement = document.createElement("label");
        labelElement.setAttribute("class", "govuk-label govuk-checkboxes__label govuk-!-padding-right-0");
        labelElement.setAttribute("for", "selected");

        container.appendChild(fieldset);
        fieldset.appendChild(container2);
        container2.appendChild(container3);
        container3.appendChild(inputElement);
        container3.appendChild(labelElement);

        const checkboxContainer = document.getElementById(this.CHECK_ALL_CHECKBOX);

        checkboxContainer.appendChild(container);

    }

    addEventListeners() {
        for (let checkbox of document.querySelectorAll('[data-check-trackedmodel]')) {
            checkbox.onchange = this.toggleCheckbox.bind(this);
        }
    }
}

const initCheckboxes = () => {
    const measurePage = document.querySelector("#measure-select-checkboxes-script");
    if (measurePage) {
        new CheckBoxes("measures");
    } else new CheckBoxes();
}

export default initCheckboxes;