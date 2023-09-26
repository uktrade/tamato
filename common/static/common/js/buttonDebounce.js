let button = document.querySelectorAll('span.add-debounce > button')[0]

const debounceButton = () => {
    if (!button) {
        return
    } else if (button) {
        addEventListener('submit', function() {
            button.disabled = true,
            alert("Your action is being processed and the submit button is now disabled. You will be taken to a confirmation screen once the action has been processed.")}
        )
    }
}

export default debounceButton;