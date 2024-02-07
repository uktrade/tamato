import React from 'react';
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
      <form action={assignUsersUrl} method="POST">
        <input type="hidden" value={CSRF_TOKEN} name="csrfmiddlewaretoken"/>
        <div className="govuk-form-group">
          <label className="govuk-label" htmlFor={elementId}>
            {label}
          </label>
          <div id={`${elementName}-hint`} className="govuk-hint">
            {hint}
          </div>
          <select
            required={true}
            id={elementId}
            name={elementName}
          >
            <option value="">Select a user</option>
            {users.map(user => 
              <option key={user.pk} value={user.pk}>{user.name}</option>
            )}
          </select>
        </div>
        <div className="govuk-form-group">
          <input type="hidden" name="assignment_type" value={assignmentType}/>
        </div>
        <button type="submit" className="govuk-button" data-prevent-double-click="true">Save</button>
      </form>
    </>
  )
}

export { AssignUserForm };
