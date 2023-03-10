

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


const setupCopyToNextDuties = (el, dutiesInputSelector) => {
    let wrapper = document.createElement("div");
    wrapper.classList.add("tap-copy-down-wrapper");
    wrapper.style.display = "flex";
    wrapper.style.flexDirection = "row";

    let button = document.createElement("button");
    button.classList.add("tap-copy-down");
    button.style.display = "block";
    button.style.width = el.offsetHeight + "px";
    button.style.height = el.offsetHeight + "px";
    button.onclick = (event) => {
        event.preventDefault();
        const nextEl = getNextDOMElement(el, dutiesInputSelector);
        if (nextEl) {
            nextEl.value = el.value;
        }
    }

    el.parentNode.insertBefore(wrapper, el);
    wrapper.appendChild(el);
    wrapper.appendChild(button);
}


const initCopyToNextDuties = () => {
    const dutiesInputSelector = "input.duties";

    for (let el of document.querySelectorAll(dutiesInputSelector)) {
        setupCopyToNextDuties(el, dutiesInputSelector);
    }
}


export { initCopyToNextDuties }
