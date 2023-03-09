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

  const btn = document.querySelector("#add-form");

  console.log(btn);

  if (btn) {
    btn.addEventListener("click", add_form);
  }
}

function add_form() {
  let fieldsets = document.getElementsByTagName("fieldset");
  let fieldset = fieldsets[0].cloneNode(true);
  let form_count = fieldsets.length

  contents = fieldset.innerHTML;
  new_contents = contents.replaceAll("formset-0", "formset-" + form_count);
  fieldset.innerHTML = new_contents

  let formset = fieldsets[0].parentNode;
  let buttons = document.getElementsByClassName("govuk-button-group")[0]

  formset.insertBefore(fieldset, buttons);
  fieldset.scrollIntoView();

  let total_forms = document.getElementById("id_measure_commodities_duties_formset-TOTAL_FORMS");
  let total_form_count = Number(total_forms.value);

  total_forms.value = total_form_count + 1;

  let max_forms = document.getElementById("id_measure_commodities_duties_formset-MAX_NUM_FORMS");
  let max_num_forms = Number(max_forms.value);

  if (total_form_count == max_num_forms - 1) {
      btn.remove();
  }
}


//export default initAutocomplete;
export { initAutocomplete, initAddNewEnhancement }
