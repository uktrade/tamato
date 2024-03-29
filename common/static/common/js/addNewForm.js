import { autoCompleteElement } from "./autocomplete";
import { setupClickHandler } from "./copyDuties";

const addNewForm = (event) => {
  event.preventDefault();

  let numForms = document.querySelectorAll("fieldset").length;
  let fieldset = document.querySelector("fieldset");
  let formset = fieldset.parentNode;
  let newForm = fieldset.cloneNode(true);

  newForm.innerHTML = newForm.innerHTML.replaceAll("-0-", "-" + numForms + "-");
  if (newForm.querySelector(".autocomplete"))
    newForm
      .querySelector(".autocomplete")
      .removeAttribute("data-original-value");

  let formFields = newForm.querySelectorAll("input");
  for (let field of formFields.values()) {
    field.value = "";
  }

  if (newForm.querySelector(".autocomplete__wrapper")) {
    newForm.querySelector(".autocomplete__wrapper").remove();
    autoCompleteElement(newForm.querySelector(".autocomplete"));
  }

  let buttonGroup = document.querySelector(".govuk-button-group");
  formset.insertBefore(newForm, buttonGroup);

  let addNewButton = document.querySelector("#add-new");
  addNewButton.scrollIntoView(false);

  let dutiesInput = newForm.querySelector("input.duties");
  let copyButton = newForm.querySelector("button.tap-copy-down");
  if (dutiesInput && copyButton) {
    setupClickHandler(dutiesInput, copyButton);
  }

  let totalForms = document.querySelector('[id$="-TOTAL_FORMS"]');
  let numTotalForms = Number(totalForms.value);
  totalForms.value = numTotalForms + 1;

  let maxForms = document.querySelector('[id$="-MAX_NUM_FORMS"]');
  let numMaxForms = Number(maxForms.value);
  if (numForms == numMaxForms - 1) {
    addNewButton.remove();
  }
};

const initAddNewEnhancement = () => {
  const btn = document.querySelector("#add-new");

  if (btn) {
    btn.addEventListener("click", addNewForm);
  }
};

export { initAddNewEnhancement };
