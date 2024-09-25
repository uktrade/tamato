import { fireEvent, render, screen } from "@testing-library/react";
import renderer from "react-test-renderer";

import { QuotaOriginFormset } from "../index";

const mockGeoAreaOptions = [
  {
    name: "All countries",
    value: 1,
  },
  {
    name: "EU",
    value: 2,
  },
  {
    name: "China",
    value: 3,
  },
  {
    name: "South Korea",
    value: 4,
  },
  {
    name: "Switzerland",
    value: 5,
  },
];

const mockGroupsWithMembers = {
  1: [3, 4, 5],
  2: [5],
};

const mockExclusionsOptions = [
  {
    name: "China",
    value: 3,
  },
  {
    name: "South Korea",
    value: 4,
  },
  {
    name: "Switzerland",
    value: 5,
  },
];

const mockOrigins = [
  {
    id: 1,
    pk: 1,
    exclusions: [
      { id: 3, pk: 1 },
      { id: 4, pk: 2 },
    ],
    geographical_area: 1,
    start_date_0: 1,
    start_date_1: 1,
    start_date_2: 2000,
    end_date_0: 1,
    end_date_1: 1,
    end_date_2: 2010,
  },
  {
    id: 2,
    pk: 2,
    exclusions: [{ id: 5, pk: 3 }],
    geographical_area: 2,
    start_date_0: 1,
    start_date_1: 1,
    start_date_2: 2000,
    end_date_0: 1,
    end_date_1: 1,
    end_date_2: 2010,
  },
];

describe("QuotaOriginFormset", () => {
  it("renders formset with props", () => {
    const mockOriginsErrors = {};

    const component = renderer.create(
      <QuotaOriginFormset
        data={mockOrigins}
        geoAreasOptions={mockGeoAreaOptions}
        exclusionsOptions={mockExclusionsOptions}
        groupsWithMembers={mockGroupsWithMembers}
        errors={mockOriginsErrors}
      />,
    );

    let tree = component.toJSON();
    expect(tree).toMatchSnapshot();
  });

  it("renders empty formset when no initial data", () => {
    const mockOriginsErrors = {};
    const mockOrigins = [];

    const component = renderer.create(
      <QuotaOriginFormset
        data={mockOrigins}
        geoAreasOptions={mockGeoAreaOptions}
        exclusionsOptions={mockExclusionsOptions}
        groupsWithMembers={mockGroupsWithMembers}
        errors={mockOriginsErrors}
      />,
    );

    let tree = component.toJSON();
    expect(tree).toMatchSnapshot();
  });

  it("renders with formset errors", () => {
    const mockOriginsErrors = {
      "origins-0-end_date":
        "The end date must be the same as or after the start date.",
    };

    const component = renderer.create(
      <QuotaOriginFormset
        data={mockOrigins}
        geoAreasOptions={mockGeoAreaOptions}
        exclusionsOptions={mockExclusionsOptions}
        groupsWithMembers={mockGroupsWithMembers}
        errors={mockOriginsErrors}
      />,
    );

    let tree = component.toJSON();
    expect(tree).toMatchSnapshot();
  });

  it("should add empty origin form when add button is clicked", () => {
    const mockOrigins = [];
    const mockOriginsErrors = {};

    // render form with no origins
    render(
      <QuotaOriginFormset
        data={mockOrigins}
        geoAreasOptions={mockGeoAreaOptions}
        exclusionsOptions={mockExclusionsOptions}
        groupsWithMembers={mockGroupsWithMembers}
        errors={mockOriginsErrors}
      />,
    );

    // add an empty origin
    fireEvent.click(screen.getByText("Add another origin"));
    expect(screen.getByText("Origin 1")).toBeInTheDocument();
    expect(screen.queryByText("Origin 2")).toBeInTheDocument();
    expect(screen.queryByText("Origin 3")).not.toBeInTheDocument();
  });

  it("should remove origin form when delete button is clicked", () => {
    const mockOriginsErrors = {};

    // render form with 2 origins
    render(
      <QuotaOriginFormset
        data={mockOrigins}
        geoAreasOptions={mockGeoAreaOptions}
        exclusionsOptions={mockExclusionsOptions}
        groupsWithMembers={mockGroupsWithMembers}
        errors={mockOriginsErrors}
      />,
    );

    // delete the last origin
    fireEvent.click(screen.getByText("Delete this origin"));
    expect(screen.getByText("Origin 1")).toBeInTheDocument();
    expect(screen.queryByText("Origin 2")).not.toBeInTheDocument();
  });
});
