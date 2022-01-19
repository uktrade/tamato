const toggleCheckAll = (event) => {
    const checkboxSelector = event.target.dataset.checkAll;
    const checkedState = event.target.checked;
    for (let checkbox of document.querySelectorAll('[' + checkboxSelector + ']')) {
        checkbox.checked = checkedState;
    }
}

const initCheckAllCheckboxes = () => {
    for (let masterCheckbox of document.querySelectorAll('[data-check-all]')) {
        masterCheckbox.onclick = toggleCheckAll;
    }
}

export default initCheckAllCheckboxes;
