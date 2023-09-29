const tapDebounce = (event) => {
    let DEBOUNCE_TIMEOUT_IN_SECONDS = 5;
    let target = event.target;
    if (target.tapDebounceFormSubmitTimer) {
      event.preventDefault();
      return false;
    }

    let targetDefaultCursor = target.style.cursor;

    target.tapDebounceFormSubmitTimer = setTimeout(
      function () {
        target.tapDebounceFormSubmitTimer = null;
        target.style.cursor = targetDefaultCursor;
      }.bind(target),
      DEBOUNCE_TIMEOUT_IN_SECONDS * 1000
    );
    target.style.cursor = "wait";
};


const initTapDebounce = () => {
  document.querySelectorAll("[data-prevent-double-click").forEach(
    (element) => {
        
      element.addEventListener('click', tapDebounce);
    }
  )
}

export default initTapDebounce;