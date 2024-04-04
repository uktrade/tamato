import renderer from "react-test-renderer";
import { fireEvent, render, screen } from "@testing-library/react";

import { WorkbasketUserAssignment } from "../index";

const mockUsers = [
  {
    pk: 1,
    name: "User One",
  },
  {
    pk: 2,
    name: "User Two",
  },
  {
    pk: 3,
    name: "User Three",
  },
];

describe("WorkbasketUserAssignment", () => {
  beforeAll(() => {
    window.CSRF_TOKEN = "abc123";
    window.assignUsersUrl = "/workbaskets/1/assign-users/";
    window.unassignUsersUrl = "/workbaskets/1/unassign-users/";
  });

  afterAll(() => {
    delete window.CSRF_TOKEN;
    delete window.assignUsersUrl;
    delete window.unassignUsersUrl;
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("renders assign workers button", () => {
    const component = renderer.create(
      <WorkbasketUserAssignment
        action="Assign"
        assignment="workers"
        users={mockUsers}
        buttonId="assign-workers"
        formId="assign-workers-form"
      />
    );

    let tree = component.toJSON();
    expect(tree).toMatchSnapshot();
  });

  it("renders assign reviewers button", () => {
    const component = renderer.create(
      <WorkbasketUserAssignment
        action="Assign"
        assignment="reviewers"
        users={mockUsers}
        buttonId="assign-reviewers"
        formId="assign-reviewers-form"
      />
    );

    let tree = component.toJSON();
    expect(tree).toMatchSnapshot();
  });

  it("renders unassign workers button", () => {
    const component = renderer.create(
      <WorkbasketUserAssignment
        action="Unassign"
        assignment="workers"
        users={mockUsers}
        buttonId="assign-workers"
        formId="assign-workers-form"
      />
    );

    let tree = component.toJSON();
    expect(tree).toMatchSnapshot();
  });

  it("renders unassign reviewers button", () => {
    const component = renderer.create(
      <WorkbasketUserAssignment
        action="Unassign"
        assignment="reviewers"
        users={mockUsers}
        buttonId="unassign-reviewers"
        formId="unassign-reviewers-form"
      />
    );

    let tree = component.toJSON();
    expect(tree).toMatchSnapshot();
  });

  it("creates form when button is clicked", () => {
    const assignmentRow = document.createElement("div");
    assignmentRow.classList.add("govuk-summary-list__row");

    render(
      <WorkbasketUserAssignment
        action="Assign"
        assignment="workers"
        users={mockUsers}
        buttonId="assign-workers"
        formId="assign-workers-form"
      />,
      {
        container: document.body.appendChild(assignmentRow),
      }
    );

    fireEvent.click(screen.getByTestId("assign-workers"));
    expect(screen.getByLabelText("Assign user")).toBeInTheDocument();
  });

  it("removes form when button is clicked twice", () => {
    const assignmentRow = document.createElement("div");
    assignmentRow.classList.add("govuk-summary-list__row");

    render(
      <WorkbasketUserAssignment
        action="Unassign"
        assignment="workers"
        users={mockUsers}
        buttonId="unassign-workers"
        formId="unassign-workers-form"
      />,
      {
        container: document.body.appendChild(assignmentRow),
      }
    );

    fireEvent.click(screen.getByTestId("unassign-workers"));
    expect(screen.getByLabelText("Unassign user")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("unassign-workers"));
    expect(screen.queryByLabelText("Unassign user")).not.toBeInTheDocument();
  });
});
