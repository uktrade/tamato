import accessibleAutocomplete from 'accessible-autocomplete'

const template = (result) => result && result.label

const initAutocomplete = () => { 
  for (let element of document.querySelectorAll(".autocomplete")) {
    const hiddenInput = element.querySelector("input[type=hidden]");
    accessibleAutocomplete({
      element: element.querySelector(".autocomplete-container"),
      id: hiddenInput.id + "_autocomplete",
      source: (query, populateResults) => {
        const source_url = element.dataset.sourceUrl;
        const searchParams = new URLSearchParams();
        searchParams.set("search", query);
        searchParams.set("format", "json");
        fetch(`${source_url}?${searchParams}`)
          .then(response => response.json())
          .then(data => populateResults(data.results));
      },
      defaultValue: element.dataset.originalValue,
      name: `${hiddenInput.name}_autocomplete`,
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
    });
  }
}

export default initAutocomplete;