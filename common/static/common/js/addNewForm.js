import { autoCompleteElement } from './autocomplete';

const addNewForm = (event) => {
    event.preventDefault();
  
    let addNewButton = document.querySelector("#add-new");
    let buttonGroup = document.querySelector(".govuk-button-group");
  
    let numForms = document.querySelectorAll("fieldset").length;
    let fieldset  = document.querySelector("fieldset");
    let formset = fieldset.parentNode;
    let newForm = fieldset.cloneNode(true);
    let formFields = newForm.querySelectorAll("input");
    
    newForm.innerHTML = newForm.innerHTML.replaceAll("formset-0", "formset-" + numForms);
    newForm.querySelector(".autocomplete").removeAttribute("data-original-value");
    for (let field of formFields.values()) {
      field.value = null;
    }
    newForm.querySelector(".autocomplete__wrapper").remove();
    autoCompleteElement(newForm.querySelector(".autocomplete"));
  
    formset.insertBefore(newForm, buttonGroup);
    addNewButton.scrollIntoView(false);
  
    let totalForms = document.querySelector('[id$="-TOTAL_FORMS"]');
    let numTotalForms = Number(totalForms.value);
    totalForms.value = numTotalForms + 1;
  
    let maxForms = document.querySelector('[id$="-MAX_NUM_FORMS"]')
    let numMaxForms = Number(maxForms.value);
    if (numForms == numMaxForms - 1) {
      addNewButton.remove();
    }
  }

const initAddNewEnhancement = () => {
    const btn = document.querySelector("#add-new");
    if (btn) {
        btn.addEventListener("click", addNewForm);
    }
  }


export { initAddNewEnhancement }
