const removeQuotaDefinitionForm = (event) => {
    event.preventDefault();
    let remove_id = event.target.id;
    let remove_number = remove_id.split('_').at(-1)
  
    let fieldset_id = 'quota-definition-row-' + remove_number

    let fieldset_to_remove = document.querySelector(".quota-definition-row-" + remove_number)
    fieldset_to_remove.remove()

    let addNewButton = document.querySelector("#add-new-definition");
    let numForms = document.querySelectorAll(".quota-definition-row").length;
    if (numForms < 10) {
      addNewButton.style.display = "inline"
    }

  }

export { removeQuotaDefinitionForm }
