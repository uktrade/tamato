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
    console.log(element);
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

  let numForms = document.querySelectorAll("fieldset").length;
  let buttonGroup = document.querySelector(".govuk-button-group");
  let addNewButton = document.querySelector("#add-new");
  let fieldset  = document.querySelector("fieldset");
  let formset = fieldset.parentNode;

  let newForm = fieldset.cloneNode(true);
  newForm.querySelector(".autocomplete__wrapper").remove();
  newForm.innerHTML = newForm.innerHTML.replaceAll("formset-0", "formset-" + numForms);
  let fieldInputs = newForm.querySelectorAll("input")
  for (let input of fieldInputs.values()) {
    input.value = null;
  }
  autoCompleteElement(newForm.querySelector(".autocomplete"));
  formset.insertBefore(newForm, buttonGroup);

  addNewButton.scrollIntoView(false);

  let totalForms = document.querySelector("#id_measure_commodities_duties_formset-TOTAL_FORMS");
  let numTotalForms = Number(totalForms.value);
  totalForms.value = numTotalForms + 1;
}


//export default initAutocomplete;
export { initAutocomplete, initAddNewEnhancement }
