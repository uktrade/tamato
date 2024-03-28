/* global CSRF_TOKEN:readonly, unassignUsersUrl:readonly */

import React, { useEffect } from "react";
import accessibleAutocomplete from "accessible-autocomplete";
import PropTypes from "prop-types";

function UnassignUserForm({ users }) {
  const elementId = "assignments-select";
  const elementName = "assignments";
  const label = "Unassign user";
  const hint = "Select a user to unassign";

  useEffect(() => {
    const selectElement = document.getElementById(elementId);
    if (selectElement)
      accessibleAutocomplete.enhanceSelectElement({
        autoselect: false,
        defaultValue: "",
        minLength: 2,
        showAllValues: true,
        selectElement: selectElement,
      });
  }, []);

  return (
    <form
      action={unassignUsersUrl}
      method="POST"
      data-testid={"unassign-user-form"}
    >
      <input type="hidden" value={CSRF_TOKEN} name="csrfmiddlewaretoken" />
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
          data-testid="unassign-user-select"
        >
          <option value="">Select a user</option>
          {users.map((user) => (
            <option key={user.pk} value={user.pk}>
              {user.name}
            </option>
          ))}
        </select>
      </div>
      <button
        type="submit"
        className="govuk-button"
        data-prevent-double-click="true"
      >
        Save
      </button>
    </form>
  );
}

UnassignUserForm.propTypes = {
  users: PropTypes.arrayOf(
    PropTypes.shape({
      pk: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
    })
  ),
};

export { UnassignUserForm };
