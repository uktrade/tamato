const addNewForm = (event) => {
    event.preventDefault();

    let numForms = document.querySelectorAll(".quota-definition-row").length;
    let fieldset  = document.querySelector(".quota-definition-row");
    let formset = fieldset.parentNode;
    let newForm = fieldset.cloneNode(true);

    newForm.innerHTML = newForm.innerHTML.replaceAll('name="volume_0"', 'name="volume_' + numForms + '"');
    newForm.innerHTML = newForm.innerHTML.replaceAll('name="start_date_0_0"', 'name="start_date_' + numForms + '_0"');
    newForm.innerHTML = newForm.innerHTML.replaceAll('name="start_date_0_1"', 'name="start_date_' + numForms + '_1"');
    newForm.innerHTML = newForm.innerHTML.replaceAll('name="start_date_0_2"', 'name="start_date_' + numForms + '_2"');
    newForm.innerHTML = newForm.innerHTML.replaceAll('name="end_date_0_0"', 'name="end_date_' + numForms + '_0"');
    newForm.innerHTML = newForm.innerHTML.replaceAll('name="end_date_0_1"', 'name="end_date_' + numForms + '_1"');
    newForm.innerHTML = newForm.innerHTML.replaceAll('name="end_date_0_2"', 'name="end_date_' + numForms + '_2"');

    let formFields = newForm.querySelectorAll("input");
    for (let field of formFields.values()) {
      field.value = "";
    }

    let submitButton = document.getElementById("submit-id-submit");
    formset.insertBefore(newForm, submitButton);

    let addNewButton = document.querySelector("#add-new-definition");
    addNewButton.scrollIntoView(false);
  }

const initAddNewDefinition = () => {
    const btn = document.querySelector("#add-new-definition");

    if (btn) {
      btn.addEventListener("click", addNewForm);
    }
  }

export { initAddNewDefinition }
