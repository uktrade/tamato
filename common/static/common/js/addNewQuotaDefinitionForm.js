import { removeQuotaDefinitionForm } from "./removeQuotaDefinitionForm.js"

let formCounter = 1

const addNewForm = (event) => {
    event.preventDefault();

    let fieldset  = document.querySelector(".quota-definition-row");
    let formset = fieldset.parentNode;
    let newForm = fieldset.cloneNode(true);

    let new_class = "quota-definition-row-" + formCounter
    newForm.classList.add(new_class)

    newForm.innerHTML = newForm.innerHTML.replaceAll('name="volume_0"', 'name="volume_' + formCounter + '"');
    newForm.innerHTML = newForm.innerHTML.replaceAll('name="start_date_0_0"', 'name="start_date_' + formCounter + '_0"');
    newForm.innerHTML = newForm.innerHTML.replaceAll('name="start_date_0_1"', 'name="start_date_' + formCounter + '_1"');
    newForm.innerHTML = newForm.innerHTML.replaceAll('name="start_date_0_2"', 'name="start_date_' + formCounter + '_2"');
    newForm.innerHTML = newForm.innerHTML.replaceAll('name="end_date_0_0"', 'name="end_date_' + formCounter + '_0"');
    newForm.innerHTML = newForm.innerHTML.replaceAll('name="end_date_0_1"', 'name="end_date_' + formCounter + '_1"');
    newForm.innerHTML = newForm.innerHTML.replaceAll('name="end_date_0_2"', 'name="end_date_' + formCounter + '_2"');

    let removeFormID = "form-remove_" + formCounter;
    newForm.insertAdjacentHTML("beforeend", `<div><a id="${removeFormID}" class="govuk-link govuk-form-group remove-quota-definition" href="#" style="font-size:19px" >Remove</a><br></div>`);
    let remove_button = newForm.lastChild
    remove_button.addEventListener("click", removeQuotaDefinitionForm);

    let formFields = newForm.querySelectorAll("input");
    for (let field of formFields.values()) {
      field.value = "";
    }

    let buttonGroup = document.querySelector('.govuk-button-group');
    formset.insertBefore(newForm, buttonGroup);

    let numForms = document.querySelectorAll(".quota-definition-row").length;

    let addNewButton = document.querySelector("#add-new-definition");
    addNewButton.scrollIntoView(false);
    formCounter += 1;
    if (numForms >= 10) {
      addNewButton.style.display = "none";
    }

  }

const initAddNewDefinition = () => {
    const btn = document.querySelector("#add-new-definition");

    if (btn) {
      btn.addEventListener("click", addNewForm);
    }
  }

export { initAddNewDefinition }
