// TODO: adjust the pathname filter to account for all objects search/filter pages
const initOpenCloseAccordionSection = () => {
    document.addEventListener('DOMContentLoaded', function() {

        let expandedSection = document.getElementById('accordion-open-close-section')
        let pathname = window.location.pathname
        if(expandedSection){
            if (pathname.includes('search')){
                expandedSection.classList.add('govuk-accordion__section--expanded');
            } else if (!pathname.includes('search')){
                expandedSection.classList.remove('govuk-accordion__section--expanded');
            }
        }
    }
    )
}

export default initOpenCloseAccordionSection;