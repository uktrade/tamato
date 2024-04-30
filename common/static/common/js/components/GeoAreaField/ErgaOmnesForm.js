import React from "react";
import PropTypes from "prop-types";
import Select from "react-select";

function ErgaOmnesForm({
  fieldsPrefix,
  renderCondition,
  ergaOmnesExclusionsInitial,
  exclusionsOptions,
}) {
  if (renderCondition) {
    return (
      <div className="govuk-radios__conditional">
        <div className="govuk-form-group">
          <div className="govuk-hint">
            Select one or more countries to be excluded:
          </div>
          <Select
            className="react-select-container"
            classNamePrefix="react-select"
            options={exclusionsOptions}
            defaultValue={ergaOmnesExclusionsInitial}
            isMulti={true}
            name={`${fieldsPrefix}-erga_omnes_exclusions`}
          />
        </div>
      </div>
    );
  }
}

ErgaOmnesForm.propTypes = {
  fieldsPrefix: PropTypes.string.isRequired,
  renderCondition: PropTypes.bool,
  ergaOmnesExclusionsInitial: PropTypes.arrayOf(PropTypes.number),
  exclusionsOptions: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.number.isRequired,
    }),
  ).isRequired,
};

export { ErgaOmnesForm };
