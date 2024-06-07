import { fireEvent, render, screen } from "@testing-library/react";
import renderer from "react-test-renderer";

import { GeoAreaField } from "../index";

const mockGroupsOptions = [
  {
    label: "EU",
    value: 11,
  },
  {
    label: "Central America",
    value: 12,
  },
  {
    label: "Channel Islands",
    value: 13,
  },
];

const mockCountryRegionsOptions = [
  {
    label: "China",
    value: 2,
  },
  {
    label: "Costa Rica",
    value: 3,
  },
  {
    label: "Jersey",
    value: 4,
  },
  {
    label: "Germany",
    value: 5,
  },
  {
    label: "Latvia",
    value: 6,
  },
  {
    label: "Panama",
    value: 7,
  },
  {
    label: "Guernsey",
    value: 8,
  },
  {
    label: "Sweden",
    value: 9,
  },
];

const mockGroupsWithMembers = {
  11: [5, 6, 9],
  12: [3, 7],
  13: [4, 8],
};

const mockExclusionsOptions = [
  ...mockGroupsOptions,
  ...mockCountryRegionsOptions,
];

describe("GeoAreaField", () => {
  it("renders field with props", () => {
    const mockInitial = {
      geoAreaType: "GROUP",
      geographicalAreaGroup: 11,
      ergaOmnesExclusions: [],
      geoGroupExclusions: [5],
      countryRegions: [],
    };

    const component = renderer.create(
      <GeoAreaField
        initial={mockInitial}
        exclusionsOptions={mockExclusionsOptions}
        groupsOptions={mockGroupsOptions}
        countryRegionsOptions={mockCountryRegionsOptions}
        groupsWithMembers={mockGroupsWithMembers}
      />,
    );

    let tree = component.toJSON();
    expect(tree).toMatchSnapshot();
  });

  it("renders empty field when no initial data", () => {
    const mockInitial = {
      geoAreaType: "ERGA_OMNES",
      geographicalAreaGroup: "",
      ergaOmnesExclusions: [],
      geoGroupExclusions: [],
      countryRegions: [],
    };

    const component = renderer.create(
      <GeoAreaField
        initial={mockInitial}
        exclusionsOptions={mockExclusionsOptions}
        groupsOptions={mockGroupsOptions}
        countryRegionsOptions={mockCountryRegionsOptions}
        groupsWithMembers={mockGroupsWithMembers}
      />,
    );

    let tree = component.toJSON();
    expect(tree).toMatchSnapshot();
  });

  it("should show the correct subform and hide other forms when radio option is clicked", () => {
    const mockInitial = {
      geoAreaType: "ERGA_OMNES",
      geographicalAreaGroup: "",
      ergaOmnesExclusions: [],
      geoGroupExclusions: [],
      countryRegions: [],
    };

    // render field with erga omnes selected
    render(
      <GeoAreaField
        initial={mockInitial}
        exclusionsOptions={mockExclusionsOptions}
        groupsOptions={mockGroupsOptions}
        countryRegionsOptions={mockCountryRegionsOptions}
        groupsWithMembers={mockGroupsWithMembers}
      />,
    );

    // click group radio option
    fireEvent.click(screen.getByText("A group of countries"));
    expect(screen.getByTestId("group_select")).toBeInTheDocument();
    expect(
      screen.queryByTestId("erga_omnes_exclusions_select"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("country_region_select"),
    ).not.toBeInTheDocument();

    // click country radio option
    fireEvent.click(screen.getByText("Specific countries or regions"));
    expect(screen.getByTestId("country_region_select")).toBeInTheDocument();
    expect(screen.queryByTestId("group_select")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("erga_omnes_exclusions_select"),
    ).not.toBeInTheDocument();

    // click erga omnes radio option
    fireEvent.click(screen.getByText("All countries (erga omnes)"));
    expect(
      screen.getByTestId("erga_omnes_exclusions_select"),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("group_select")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("country_region_select"),
    ).not.toBeInTheDocument();
  });

  it.skip("should update the exclusions options list when a group is selected", () => {
    const mockInitial = {
      geoAreaType: "GROUP",
      geographicalAreaGroup: "",
      ergaOmnesExclusions: [],
      geoGroupExclusions: [],
      countryRegions: [],
    };

    render(
      <GeoAreaField
        initial={mockInitial}
        exclusionsOptions={mockExclusionsOptions}
        groupsOptions={mockGroupsOptions}
        countryRegionsOptions={mockCountryRegionsOptions}
        groupsWithMembers={mockGroupsWithMembers}
      />,
    );

    // group
    fireEvent.click(screen.getAllByRole("combobox")[0]);
    fireEvent.click(screen.getByText("Channel Islands"));
    // exclusions
    fireEvent.click(screen.getAllByRole("combobox")[1]);
    expect(screen.getAllByRole("listbox").length).toBe(2);
    fireEvent.click(screen.getByText("Jersey"));

    // clicking the element with "combobox" role doesn't show the list of options
    // no idea what element has the click event handler for the select box
    // not sure how we're supposed to test this
  });
});
