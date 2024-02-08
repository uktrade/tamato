import renderer from 'react-test-renderer';
import { render, screen } from "@testing-library/react";
import { AssignUserForm } from '../AssignUserForm';


const mockUsers = [
  {
    "pk": 1,
    "name": "User One",
  },
  {
    "pk": 2,
    "name": "User Two",
  },
  {
    "pk": 3,
    "name": "User Three",
  },
]

describe(AssignUserForm, () => {
  const csrfToken = "abc123";
  const assignUsersUrl = "/workbaskets/1/assign-users/";

  beforeAll(() => {
    window.CSRF_TOKEN = csrfToken;
    window.assignUsersUrl = assignUsersUrl;
  });
  
  afterAll(() => {
    delete window.CSRF_TOKEN;
    delete window.assignUsersUrl;
  });

  it('renders form', () => {
    const component = renderer.create(
      <AssignUserForm
        assignmentType={"WORKBASKET_WORKER"}
        users={mockUsers}
      />
    );

    let tree = component.toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('has assign users form action url', () => {
    render(
      <AssignUserForm
        assignmentType={"WORKBASKET_WORKER"}
        users={mockUsers}
      />
    );

    expect(screen.getByTestId("assign-user-form")).toHaveAttribute('action', assignUsersUrl);
  });
})