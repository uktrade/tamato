// Sets up conditional rendering for all MeasureCondition fieldsets

import { nodeListForEach } from './util.js'

// Generic visibility change function
const changeElementVisibility = (triggerElement, displayElement, triggerProperty) => {
    displayElement.style.display = 
        (triggerElement.selectedOptions[0].dataset[triggerProperty] == 'True') 
        ? 'block' 
        : 'none'
}

// Sets up conditional rendering for an individual MeasureCondition fieldset
const applyConditionalRendering = (parent, id) => {
    // Gets reference elements
    let conditionCodeElement = parent.querySelector(`#id_conditions-${id}-condition_code`)
    let actionCodeElement = parent.querySelector(`#id_conditions-${id}-action`)

    // Gets changeable elements
    let certificateElement = parent.querySelector(`#div_id_conditions-${id}-required_certificate`)
    let referencePriceElement = parent.querySelector(`#div_id_conditions-${id}-reference_price`)
    let dutyElement = parent.querySelector(`#div_id_conditions-${id}-applicable_duty`)
    
    // Functions to set element visibility based on specific triggers
    let changeConditionCodeDependencies = () => {
        changeElementVisibility(conditionCodeElement, certificateElement, 'certificate')
        changeElementVisibility(conditionCodeElement, referencePriceElement, 'price')
    }
    let changeActionCodeDependency = () => {
        changeElementVisibility(actionCodeElement, dutyElement, 'duty')
    }

    // Sets initial display choices
    changeConditionCodeDependencies()
    changeActionCodeDependency()

    // Activates change visibilty on select
    conditionCodeElement.addEventListener("change", () => changeConditionCodeDependencies())
    actionCodeElement.addEventListener("change", () => changeActionCodeDependency())
}

// Applies conditional rendering for all MeasureConditions in a form
const initConditionalMeasureConditions = () => {
    let conditionalMeasureFieldsets = document.querySelectorAll('[data-field="condition_code"]')

    nodeListForEach(conditionalMeasureFieldsets, (conditionalMeasureForm, i) => {
        applyConditionalRendering(conditionalMeasureForm, i)
    });
}

export default initConditionalMeasureConditions;
