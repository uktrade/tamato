import accessibleAutocomplete from "accessible-autocomplete";

import { removeNewLine, cleanResults } from "./util.js";

// Only a new result has a label, else result is the original result's label
const template = (result) =>
  typeof result == "object" ? result.label : result;

let aborter = null;

const autoCompleteElement = (element, includeNameAttr = true) => {
  const hiddenInput = element.querySelector("input[type=hidden]");
  const params = {
    element: element.querySelector(".autocomplete-container"),
    id: hiddenInput.id + "_autocomplete",
    source: (query, populateResults) => {
      const sourceUrl = element.dataset.sourceUrl;
      const searchParams = new URLSearchParams();
      searchParams.set("search", query);
      searchParams.set("format", "json");
      if (aborter) {
        aborter.abort();
      }
      aborter = new AbortController();
      const signal = aborter.signal;
      fetch(`${sourceUrl}?${searchParams}`, { signal })
        .then((response) => response.json())
        .then((data) => populateResults(cleanResults(data.results)))
        .catch((err) => console.error(err));
    },
    minLength: element.dataset.minLength ? element.dataset.minLength : 0,
    defaultValue:
      element.dataset.originalValue &&
      removeNewLine(element.dataset.originalValue),
    name: "",
    templates: {
      inputValue: template,
      suggestion: template,
    },
    onConfirm: (value) => {
      const autocomplete = document.querySelector(
        `#${hiddenInput.id}_autocomplete`
      );
      if (value && typeof value == "object") {
        // value is new
        hiddenInput.value = value.value;
      } else if (!autocomplete.value) {
        hiddenInput.value = "";
      }
    },
  };

  if (includeNameAttr) {
    params.name = `${hiddenInput.name}_autocomplete`;
  }

  accessibleAutocomplete(params);
};

const initAutocomplete = (includeNameAttr = true) => {
  for (let element of document.querySelectorAll(".autocomplete")) {
    autoCompleteElement(element, includeNameAttr);
  }
};

//export default initAutocomplete;
export { initAutocomplete, autoCompleteElement };
