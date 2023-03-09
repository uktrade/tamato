import accessibleAutocomplete from 'accessible-autocomplete'

const template = (result) => result && result.label

let aborter = null;


const autoCompleteElement = (element, includeNameAttr=true) => {
  const hiddenInput = element.querySelector("input[type=hidden]");
  const params = {
    element: element.querySelector(".autocomplete-container"),
    id: hiddenInput.id + "_autocomplete",
    source: (query, populateResults) => {
      const source_url = element.dataset.sourceUrl;
      const searchParams = new URLSearchParams();
      searchParams.set("search", query);
      searchParams.set("format", "json");
      if(aborter) {
        aborter.abort();
      }
      aborter = new AbortController();
      const signal = aborter.signal
      fetch(`${source_url}?${searchParams}`, {signal})
        .then(response => response.json())
        .then(data => populateResults(data.results))
        .catch(err => console.log(err));
    },
    minLength: element.dataset.minLength ? element.dataset.minLength : 0,
    defaultValue: element.dataset.originalValue,
    name: "",
    templates: {
      inputValue: template,
      suggestion: template
    },
    onConfirm: value => {
      const autocomplete = document.querySelector(`#${hiddenInput.id}_autocomplete`);
      if (value) {
        hiddenInput.value = value.value;
      } else if (!autocomplete.value) {
        hiddenInput.value = "";
      }
    }
  };

  if (includeNameAttr) {
    params.name = `${hiddenInput.name}_autocomplete`;
  }

  accessibleAutocomplete(params);
}


const initAutocomplete = (includeNameAttr=true) => { 
  for (let element of document.querySelectorAll(".autocomplete")) {
    autoCompleteElement(element, includeNameAttr);
  }
}

const initAddNewEnhancement = () => {
  console.log("*** initAddNewEnhancement()");

  const btn = document.querySelector("#add-new");

  console.log(btn);

  if (btn) {
    btn.addEventListener("click", addNewForm);
  }
}

function addNewForm(event) {
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


//export default initAutocomplete;
export { initAutocomplete, initAddNewEnhancement }
