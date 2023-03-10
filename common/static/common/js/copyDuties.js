const dutiesInputSelector = "input.duties";


const getNextDOMElement = (startElement, selector) => {
    /* Get the next element, that matches selector, and that comes after
    startElement within the DOM or null if no successive matching elements
    exist. startElement must be matchable usng selector.
    */

    const allElements = document.querySelectorAll(selector);
    for (let i = 0; i < allElements.length; i++) {
        if (allElements[i] == startElement) {
            if (i < allElements.length - 1) {
                return allElements[i + 1];
            } else {
                return null;
            }
        }
    }
    return null;
}


const setupClickHandler = (dutiesInput, button) => {
    /* Set up "copy to next" button click handling. dutiesInput and button
    are related elements - clicking button will copy the value from dutiesInput
    to the next duties input element in the DOM, if one exists.
    */

    button.onclick = (event) => {
        event.preventDefault();
        const nextDutiesInput = getNextDOMElement(
            dutiesInput,
            dutiesInputSelector,
        );
        if (nextDutiesInput) {
            nextDutiesInput.value = dutiesInput.value;
        }
    }
}


const setupCopyToNextDuties = (dutiesInput) => {
    /* Set up dutiesInput (an input element that will take a duties sentence)
    that is part of a form within a formset. The input element is dynamically
    wrapped by a div element and a sibling button element added to allow
    copying the duties input value to the next duties input in the DOM.
    */

    let wrapper = document.createElement("div");
    wrapper.classList.add("tap-copy-down-wrapper");
    wrapper.style.display = "flex";
    wrapper.style.flexDirection = "row";

    let button = document.createElement("button");
    button.classList.add("tap-copy-down");
    button.style.display = "block";
    button.style.width = dutiesInput.offsetHeight + "px";
    button.style.height = dutiesInput.offsetHeight + "px";
    setupClickHandler(dutiesInput, button);

    dutiesInput.parentNode.insertBefore(wrapper, dutiesInput);
    wrapper.appendChild(dutiesInput);
    wrapper.appendChild(button);
}


const initCopyToNextDuties = () => {
    /* Set up copy to next duties for a formset containing duties input
    elements. Duties input elements must must have the duties CSS class applied
    in order that selector matching can be performed againt "input.duties".
    */

    for (let dutiesInput of document.querySelectorAll(dutiesInputSelector)) {
        setupCopyToNextDuties(dutiesInput);
    }
}


export { initCopyToNextDuties, setupClickHandler }
