/* global assignableUsers:readonly, assignedWorkers:readonly, assignedReviewers:readonly */

import React, { useState } from "react";
import { createPortal } from "react-dom";
import { createRoot } from "react-dom/client";
import PropTypes from "prop-types";

import { AssignUserForm } from "./AssignUserForm";
import { UnassignUserForm } from "./UnassignUserForm";

/**
 * Renders a button that opens/closes a form to assign/unassign users.
 * @param action The form's action (Assign or Unassign)
 * @param assignment The form's assignment type (workers or reviewers)
 * @param users The form's selectable users
 * @param buttonId The button's element ID
 * @param formId The form's element ID
 */
function WorkbasketUserAssignment({
  action,
  assignment,
  users,
  buttonId,
  formId,
}) {
  const [showForm, setShowForm] = useState(null);
  const assignmentType =
    assignment == "workers" ? "WORKBASKET_WORKER" : "WORKBASKET_REVIEWER";

  const removeFormDiv = () => {
    const possibleFormDivs = [
      document.getElementById("assign-workers-form"),
      document.getElementById("unassign-workers-form"),
      document.getElementById("assign-reviewers-form"),
      document.getElementById("unassign-reviewers-form"),
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
    const assignmentButton = document.getElementById(buttonId);
    const assignmentRow = assignmentButton.closest(".govuk-summary-list__row");
    assignmentRow.classList.add("govuk-summary-list__row--no-border");
    assignmentRow.after(formDiv);
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
    if (action === "Assign")
      return <AssignUserForm assignmentType={assignmentType} users={users} />;
    else return <UnassignUserForm users={users} />;
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
        <span className="govuk-visually-hidden"> {assignment}</span>
      </button>

      {showForm !== null &&
        createPortal(<UserForm action={action} />, showForm)}
    </>
  );
}
WorkbasketUserAssignment.propTypes = {
  action: PropTypes.string.isRequired,
  assignment: PropTypes.string.isRequired,
  users: PropTypes.arrayOf(
    PropTypes.shape({
      pk: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
    }),
  ),
  buttonId: PropTypes.string.isRequired,
  formId: PropTypes.string.isRequired,
};

/**
 * Creates React roots in which to render WorkBasketUserAssignment components
 * for each assign/unassign link on the workbasket summary view.
 */
function init() {
  const assignWorkersLink = document.getElementById("assign-workers");
  if (assignWorkersLink) {
    const assignWorkers = createRoot(assignWorkersLink);
    assignWorkers.render(
      <WorkbasketUserAssignment
        action="Assign"
        assignment="workers"
        users={assignableUsers}
        buttonId="assign-workers"
        formId="assign-workers-form"
      />,
    );
  }

  const assignReviewersLink = document.getElementById("assign-reviewers");
  if (assignReviewersLink) {
    const assignReviewers = createRoot(assignReviewersLink);
    assignReviewers.render(
      <WorkbasketUserAssignment
        action="Assign"
        assignment="reviewers"
        users={assignableUsers}
        buttonId="assign-reviewers"
        formId="assign-reviewers-form"
      />,
    );
  }

  const unassignWorkersLink = document.getElementById("unassign-workers");
  if (unassignWorkersLink) {
    const unassignWorkers = createRoot(unassignWorkersLink);
    unassignWorkers.render(
      <WorkbasketUserAssignment
        action="Unassign"
        assignment="workers"
        users={assignedWorkers}
        buttonId="unassign-workers"
        formId="unassign-workers-form"
      />,
    );
  }

  const unassignReviewersLink = document.getElementById("unassign-reviewers");
  if (unassignReviewersLink) {
    const unassignReviewers = createRoot(unassignReviewersLink);
    unassignReviewers.render(
      <WorkbasketUserAssignment
        action="Unassign"
        assignment="reviewers"
        users={assignedReviewers}
        buttonId="unassign-reviewers"
        formId="unassign-reviewers-form"
      />,
    );
  }
}

function setupWorkbasketUserAssignment() {
  document.addEventListener("DOMContentLoaded", init());
}

export { setupWorkbasketUserAssignment, WorkbasketUserAssignment };
