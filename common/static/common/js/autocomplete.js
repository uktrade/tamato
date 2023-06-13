import accessibleAutocomplete from 'accessible-autocomplete'

// Only a new result has a label, else result is the original result's label
const template = (result) => typeof result == "object" ? result.label : result

let aborter = null;

const newLine  = /\n/g;
const removeNewLine = (str) => str.replace(newLine, "")

const cleanResults = (results) => {
  /*
  Results which contain new line characters are considered as a new query when
  selected, causing results to be repopulated unnecessarily. To prevent this,
  we can remove new line characters from results since they're unimportant here.
  */
  for(let i = 0, len = results.length; i < len; i++) {
    results[i].label = removeNewLine(results[i].label);
  }
  return results
}


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
        .then(data => populateResults(cleanResults(data.results)))
        .catch(err => console.log(err));
    },
    minLength: element.dataset.minLength ? element.dataset.minLength : 0,
    defaultValue: element.dataset.originalValue && removeNewLine(element.dataset.originalValue),
    name: "",
    templates: {
      inputValue: template,
      suggestion: template
    },
    onConfirm: value => {
      const autocomplete = document.querySelector(`#${hiddenInput.id}_autocomplete`);
      if (value && typeof value == "object") {
        // value is new
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


//export default initAutocomplete;
export { initAutocomplete, autoCompleteElement }
