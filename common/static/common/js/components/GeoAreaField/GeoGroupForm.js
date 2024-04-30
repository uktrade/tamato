import React, { useState } from "react";
import PropTypes from "prop-types";
import Select from "react-select";

function GeoGroupForm({
  fieldsPrefix,
  renderCondition,
  groupsWithMembers,
  geoGroupInitial,
  geoGroupExclusionsInitial,
  groupsOptions,
  exclusionsOptions,
}) {
  const [usableExclusionsOptions, setExclusionsOptions] = useState([
    ...exclusionsOptions,
  ]);
  const [geoGroupExclusions, setGeoGroupExclusions] = useState(
    geoGroupExclusionsInitial || [],
  );

  function updateExclusionOptions(e) {
    const newExclusions = exclusionsOptions.filter(
      (option) => groupsWithMembers[e.value].indexOf(option.value) >= 0,
    );
    setExclusionsOptions(newExclusions);
    // the previously selected exclusion will need to be cleared because it may not be valid
    setGeoGroupExclusions([]);
  }

  if (renderCondition) {
    return (
      <div className="govuk-radios__conditional">
        <div className="govuk-form-group">
          <Select
            className="react-select-container"
            classNamePrefix="react-select"
            options={groupsOptions}
            defaultValue={geoGroupInitial}
            onChange={updateExclusionOptions}
            name={`${fieldsPrefix}-geographical_area_group`}
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
            onChange={(value) => setGeoGroupExclusions(value)}
            isMulti={true}
            name={`${fieldsPrefix}-geo_group_exclusions`}
          />
        </div>
      </div>
    );
  }
}

GeoGroupForm.propTypes = {
  fieldsPrefix: PropTypes.string.isRequired,
  renderCondition: PropTypes.bool,
  groupsWithMembers: PropTypes.objectOf(PropTypes.number),
  geoGroupInitial: PropTypes.number,
  geoGroupExclusionsInitial: PropTypes.arrayOf(PropTypes.number),
  exclusionsOptions: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.number.isRequired,
    }),
  ).isRequired,
  groupsOptions: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.number.isRequired,
    }),
  ).isRequired,
};

export { GeoGroupForm };
