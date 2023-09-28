const tapDebounce = function(event) {
    let DEBOUNCE_TIMEOUT_IN_SECONDS = 5;

    if (this.tapDebounceFormSubmitTimer) {
        event.preventDefault();
        button.disabled = true
        return false
    }


    this.tapDebounceFormSubmitTimer = setTimeout(function () {
        this.tapDebounceFormSubmitTimer = null;
    }.bind(this), DEBOUNCE_TIMEOUT_IN_SECONDS * 1000);
};

document.querySelectorAll("[data-prevent-double-click").forEach(
    (element) => {
        element.addEventListener('click', tapDebounce);
    }
)

export default tapDebounce;