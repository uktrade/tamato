let button = document.getElementById('add-debounce')

const debounceButton = () => {
    if (button) {
        console.log('button', button)
        addEventListener('submit', function() {
            button.disabled = true,
            alert("Your action is being processed and the submit button is now disabled. You will be taken to a confirmation screen once the action has been processed.")}
        )
    }
}

export default debounceButton;