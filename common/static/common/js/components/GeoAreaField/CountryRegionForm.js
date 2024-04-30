import React from "react";
import PropTypes from "prop-types";
import Select from "react-select";

function CountryRegionForm({
  fieldsPrefix,
  renderCondition,
  countryRegionsInitial,
  countryRegionsOptions,
}) {
  if (renderCondition) {
    return (
      <div className="govuk-radios__conditional">
        <div className="govuk-form-group">
          <Select
            className="react-select-container"
            classNamePrefix="react-select"
            options={countryRegionsOptions}
            defaultValue={countryRegionsInitial}
            isMulti={true}
            max={2}
            name={`${fieldsPrefix}-countries`}
          />
        </div>
      </div>
    );
  }
}

CountryRegionForm.propTypes = {
  fieldsPrefix: PropTypes.string.isRequired,
  renderCondition: PropTypes.bool,
  countryRegionsInitial: PropTypes.arrayOf(PropTypes.number),
  countryRegionsOptions: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.number.isRequired,
    }),
  ).isRequired,
};

export { CountryRegionForm };
