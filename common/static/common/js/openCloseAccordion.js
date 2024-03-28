// TODO: adjust the pathname filter to account for all objects search/filter pages
const initOpenCloseAccordionSection = () => {
  document.addEventListener("DOMContentLoaded", function () {
    let button = document.querySelector(".govuk-accordion__open-all");
    let expandedSection = document.getElementById(
      "accordion-open-close-section"
    );
    let pathname = window.location.pathname;
    if (expandedSection) {
      if (!pathname.includes("search")) {
        button.innerHTML = "Open all";
        button.setAttribute("aria-expanded", "false");
        expandedSection.classList.remove("govuk-accordion__section--expanded");
      }
    }
  });
};

export default initOpenCloseAccordionSection;
