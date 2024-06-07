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
      <div
        className="govuk-radios__conditional"
        data-testid="country_region_select"
      >
        <div className="govuk-form-group">
          <Select
            className="react-select-container"
            classNamePrefix="react-select"
            options={countryRegionsOptions}
            defaultValue={countryRegionsInitial}
            isMulti={true}
            name={`${fieldsPrefix}-country_region`}
            id="country_region_select"
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
