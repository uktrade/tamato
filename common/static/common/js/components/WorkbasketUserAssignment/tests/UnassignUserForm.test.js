import renderer from 'react-test-renderer';
import { fireEvent, render, screen } from "@testing-library/react";
import { UnassignUserForm } from '../UnassignUserForm';


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

describe(UnassignUserForm, () => {
  const csrfToken = "abc123";
  const unassignUsersUrl = "/workbaskets/1/unassign-users/";

  beforeAll(() => {
    window.CSRF_TOKEN = csrfToken;
    window.unassignUsersUrl = unassignUsersUrl;
  });
  
  afterAll(() => {
    delete window.CSRF_TOKEN;
    delete window.unassignUsersUrl;
  });

  it('renders form', () => {
    const component = renderer.create(
      <UnassignUserForm users={mockUsers}/>
    );

    let tree = component.toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('has unassign users form action url', () => {
    render(
      <UnassignUserForm users={mockUsers}/>
    );

    expect(screen.getByTestId("unassign-user-form")).toHaveAttribute('action', unassignUsersUrl);
  });

it('does not submit when form is empty', () => {
    const mockSubmit = jest.fn();
    render( < UnassignUserForm
        users = {
            mockUsers
        }
        />
    );
    screen.getByTestId("unassign-user-form").onsubmit = mockSubmit
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(mockSubmit).not.toHaveBeenCalled();
})



it('submits with selected user', () => {
    const mockSubmit = jest.fn();
    render( < UnassignUserForm
        users = {
            mockUsers
        }
        />
    );
    screen.getByTestId("unassign-user-form").onsubmit = mockSubmit
    const input = screen.getByTestId('unassign-user-select');
    fireEvent.change(input, {
        target: {
            value: mockUsers[0].pk
        }
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(mockSubmit).toHaveBeenCalled();
})
})