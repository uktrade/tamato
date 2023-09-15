// TODO: adjust the pathname filter to account for all objects search/filter pages
const initOpenCloseAccordionSection = () => {
    document.addEventListener('DOMContentLoaded', function() {
        
        let expandedSection = document.getElementsByClassName('govuk-accordion__section')
        let pathname = window.location.pathname
        if(expandedSection.length > 0){
            if (pathname.includes('measures/search')){
                expandedSection[0].classList.add('govuk-accordion__section--expanded');
            } else if (pathname.includes('measures') && !pathname.includes('search')){
                expandedSection[0].classList.remove('govuk-accordion__section--expanded');
            }
        }
    }
    )
}

export default initOpenCloseAccordionSection;