let button = document.getElementById('add-debounce')
let infoText = document.getElementById('add-debounce-inset-text')

const debounceButton = () => {
    if (button) {
        addEventListener('submit', function() {
            button.disabled = true,
            infoText.classList.remove('js-hidden')
        })
    }
}

export default debounceButton;