import React from 'react';
import Select from 'react-select'
import { useEffect } from 'react';
import accessibleAutocomplete from 'accessible-autocomplete'


function AssignUserForm({ assignmentType, users }) {
  const elementId = "users-select"
  const elementName = "users"
  const label = "Assign user"
  const hint = "Select a user to assign"

  useEffect(() => {
    const selectElement = document.getElementById(elementId);
    if (selectElement)
      accessibleAutocomplete.enhanceSelectElement(
        {
          autoselect: false,
          defaultValue: "",
          minLength: 2,
          showAllValues: true,
          selectElement: selectElement
        }
      );
  }, [])

  return (
    <>
      <form action={assignUsersUrl} method="POST" data-testid={"assign-user-form"}>
        <input type="hidden" value={CSRF_TOKEN} name="csrfmiddlewaretoken" />
        <div className="govuk-form-group">
          <label className="govuk-label" htmlFor={elementId}>
            {label}
          </label>
          <div id={`${elementName}-hint`} className="govuk-hint">
            {hint}
          </div>
          {/* See scss/components for style overrides */}
          <Select
            required={true}
            unstyled
            isMulti
            className="react-select-container"
            classNamePrefix="react-select"
            id={elementId}
            name={elementName}
            data-testid='assign-user-select'
            options={users}
          />
        </div>
        <div className="govuk-form-group">
          <input type="hidden" name="assignment_type" value={assignmentType} />
        </div>
        <button type="submit" className="govuk-button" data-prevent-double-click="true">Save</button>
      </form>
    </>
  )
}

export { AssignUserForm };
