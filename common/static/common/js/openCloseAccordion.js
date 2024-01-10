// TODO: adjust the pathname filter to account for all objects search/filter pages
const initOpenCloseAccordionSection = () => {
    document.addEventListener('DOMContentLoaded', function() {

        // We use the default GDS accordions however in TAP we want to display our optional summaries within the accordion content rather than the header
        var accordionSections = document.querySelectorAll('.govuk-accordion__section');

        accordionSections.forEach(function(section) {
            var header = section.querySelector('.govuk-accordion__section-header');
            var content = section.querySelector('.govuk-accordion__section-content');
            var summary = header.querySelector('.govuk-accordion__section-summary');

            // Check if summary exists before moving
            if (summary) {
                // Create div for the summary
                var summaryContainer = document.createElement('div');
                summaryContainer.className = 'govuk-accordion__section-summary-container';

                // Move the summary to the container
                summaryContainer.appendChild(summary);

                // Add a line break for cleanliness
                summaryContainer.appendChild(document.createElement('br'));

                // Insert the container at the beginning of the content
                content.insertBefore(summaryContainer, content.firstChild);
            }
        });

        let expandedSection = document.getElementById('accordion-open-close-section')
        let pathname = window.location.pathname
        if(expandedSection){
            if (!pathname.includes('search')){
                expandedSection.classList.remove('govuk-accordion__section--expanded');
            }
        }
    }
    )
}

export default initOpenCloseAccordionSection;