import React, { useState } from "react";
import PropTypes from "prop-types";
import Select from "react-select";

function GeoGroupForm({
  fieldsPrefix,
  renderCondition,
  geographicalAreaGroup,
  geoGroupExclusions,
  updateForm,
  errors,
  groupsWithMembers,
  geoGroupInitial,
  geoGroupExclusionsInitial,
  groupsOptions,
  exclusionsOptions,
}) {
  const [usableExclusionsOptions, setExclusionsOptions] = useState([
    ...exclusionsOptions,
  ]);

  function handleChange(fieldName, value) {
    const newExclusions = exclusionsOptions.filter(
      (option) => groupsWithMembers[value.value].indexOf(option.value) >= 0,
    );
    setExclusionsOptions(newExclusions);
    // the previously selected exclusion will need to be cleared because it may not be valid
    updateForm(["geoGroupExclusions", fieldName], [[], value]);
  }

  if (renderCondition) {
    return (
      <div className="govuk-radios__conditional" data-testid="group_select">
        <div className="govuk-form-group">
          <Select
            className="react-select-container"
            classNamePrefix="react-select"
            options={groupsOptions}
            defaultValue={geoGroupInitial}
            value={geographicalAreaGroup}
            onChange={(value) => handleChange("geographicalAreaGroup", value)}
            name={`${fieldsPrefix}-geographical_area_group`}
            id="group_select"
            meta={{
              error: errors[`${fieldsPrefix}-geographical_area_group`],
              touched: Boolean(
                errors[`${fieldsPrefix}-geographical_area_group`],
              ),
            }}
          />
        </div>
        <div className="govuk-form-group">
          <div className="govuk-hint">
            Select one or more countries to be excluded:
          </div>
          <Select
            className="react-select-container"
            classNamePrefix="react-select"
            options={usableExclusionsOptions}
            defaultValue={geoGroupExclusionsInitial}
            value={geoGroupExclusions}
            onChange={(value) => updateForm("geoGroupExclusions", value)}
            isMulti={true}
            name={`${fieldsPrefix}-geo_group_exclusions`}
            id="group_exclusions_select"
            meta={{
              error: errors[`${fieldsPrefix}-geo_group_exclusions`],
              touched: Boolean(errors[`${fieldsPrefix}-geo_group_exclusions`]),
            }}
          />
        </div>
      </div>
    );
  }
}

GeoGroupForm.propTypes = {
  fieldsPrefix: PropTypes.string.isRequired,
  renderCondition: PropTypes.bool,
  groupsWithMembers: PropTypes.objectOf(PropTypes.arrayOf(PropTypes.number)),
  geoGroupInitial: PropTypes.shape({
    label: PropTypes.string.isRequired,
    value: PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.number]),
  }),
  geographicalAreaGroup: PropTypes.shape({
    label: PropTypes.string.isRequired,
    value: PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.number]),
  }),
  geoGroupExclusionsInitial: PropTypes.arrayOf(PropTypes.number),
  geoGroupExclusions: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.number]),
    }),
  ),
  updateForm: PropTypes.func.isRequired,
  errors: PropTypes.objectOf(PropTypes.string).isRequired,
  exclusionsOptions: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.number]),
    }),
  ).isRequired,
  groupsOptions: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.number]),
    }),
  ).isRequired,
};

export { GeoGroupForm };
