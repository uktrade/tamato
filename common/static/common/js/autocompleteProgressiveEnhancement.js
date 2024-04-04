import accessibleAutocomplete from "accessible-autocomplete";

const progressiveAutoCompleteElement = (element) => {
  const params = {
    selectElement: element,
    minLength: 2,
    autoselect: false,
    showAllValues: false,
  };

  accessibleAutocomplete.enhanceSelectElement(params);
};

const initAutocompleteProgressiveEnhancement = () => {
  for (let element of document.querySelectorAll(
    ".autocomplete-progressive-enhancement"
  )) {
    progressiveAutoCompleteElement(element);
  }
};

export { initAutocompleteProgressiveEnhancement };
