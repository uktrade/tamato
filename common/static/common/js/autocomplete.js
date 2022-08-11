import accessibleAutocomplete from 'accessible-autocomplete'

const template = (result) => result && result.label

let aborter = null;
const initAutocomplete = (includeNameAttr=true) => { 
  for (let element of document.querySelectorAll(".autocomplete")) {
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
}

export default initAutocomplete;