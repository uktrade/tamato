const initCloseAccordionSection = () => {
    document.addEventListener('DOMContentLoaded', function() {
        
        let expandedSection = document.getElementsByClassName('govuk-accordion__section')
        let pathname = window.location.pathname
        if(expandedSection.length > 0){
            if (pathname.includes('search')){
                expandedSection[0].classList.add('govuk-accordion__section--expanded');
            } else {
                expandedSection[0].classList.remove('govuk-accordion__section--expanded');
            }
        }
    }
    )
}

export default initCloseAccordionSection;