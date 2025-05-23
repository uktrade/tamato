/* global assignableUsers:readonly, currentAssignee:readonly */

import React, { useState } from "react";
import { createPortal } from "react-dom";
import { createRoot } from "react-dom/client";
import PropTypes from "prop-types";

import { AssignUserForm } from "./AssignUserForm";
import { UnassignUserForm } from "./UnassignUserForm";

/**
 * Renders a button that opens/closes a form to assign/unassign users.
 * @param action The form's action (Assign or Unassign)
 * @param users The form's selectable users
 * @param buttonId The button's element ID
 * @param formId The form's element ID
 */
function TaskUserAssignment({
  action,
  assignableUsers,
  currentAssignee,
  buttonId,
  formId,
}) {
  const [showForm, setShowForm] = useState(null);

  const removeFormDiv = () => {
    const possibleFormDivs = [
      document.getElementById("assign-user-form"),
      document.getElementById("unassign-user-form"),
    ];
    possibleFormDivs.forEach((form) => {
      if (form) {
        const assignmentRow = form.previousSibling;
        assignmentRow.classList.remove("govuk-summary-list__row--no-border");
        form.remove();
      }
    });
  };

  const createFormDiv = () => {
    const formDiv = document.createElement("div");
    formDiv.id = formId;
    formDiv.className = "govuk-!-margin-top-4";

    const assignedUsersContent = document.getElementById(
      "assigned-user-content",
    );
    assignedUsersContent.classList.add("govuk-summary-list__row--no-border");
    assignedUsersContent.after(formDiv);

    setShowForm(formDiv);
  };

  const handleClick = (e) => {
    e.preventDefault();
    const isShown = document.getElementById(formId);
    removeFormDiv();
    if (showForm && isShown) {
      setShowForm(null);
      return;
    }
    createFormDiv();
  };

  function UserForm({ action }) {
    if (action === "Assign") {
      return <AssignUserForm users={assignableUsers} />;
    } else {
      return <UnassignUserForm user={currentAssignee} />;
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        id={buttonId}
        data-testid={buttonId}
        className="govuk-link fake-link"
      >
        {action}
      </button>

      {showForm !== null &&
        createPortal(<UserForm action={action} />, showForm)}
    </>
  );
}
TaskUserAssignment.propTypes = {
  action: PropTypes.string.isRequired,
  assignableUsers: PropTypes.arrayOf(
    PropTypes.shape({
      pk: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
    }),
  ),
  currentAssignee: PropTypes.shape({
    pk: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
  }),
  buttonId: PropTypes.string.isRequired,
  formId: PropTypes.string.isRequired,
};

/**
 * Creates React roots in which to render TaskUserAssignment components
 * for each assign/unassign link on the Task detail view.
 */
function init() {
  const assignUserLink = document.getElementById("assign-user");
  if (assignUserLink) {
    const assignUser = createRoot(assignUserLink);
    assignUser.render(
      <TaskUserAssignment
        action="Assign"
        assignableUsers={assignableUsers}
        buttonId="assign-user"
        formId="assign-user-form"
      />,
    );
  }

  const unassignUserLink = document.getElementById("unassign-user");
  if (unassignUserLink) {
    const unassignUser = createRoot(unassignUserLink);
    unassignUser.render(
      <TaskUserAssignment
        action="Unassign"
        currentAssignee={currentAssignee}
        buttonId="unassign-user"
        formId="unassign-user-form"
      />,
    );
  }
}

function setupTaskUserAssignment() {
  document.addEventListener("DOMContentLoaded", init());
}

export { setupTaskUserAssignment, TaskUserAssignment };
