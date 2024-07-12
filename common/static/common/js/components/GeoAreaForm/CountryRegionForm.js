import React from "react";
import PropTypes from "prop-types";
import Select from "react-select";

function CountryRegionForm({
  fieldsPrefix,
  renderCondition,
  updateForm,
  data,
  errors,
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
            value={data.countryRegions}
            isMulti={true}
            onChange={(value) => updateForm("countryRegions", value)}
            name={`${fieldsPrefix}-country_region`}
            id="country_region_select"
            meta={{
              error: errors[`${fieldsPrefix}-country_region`],
              touched: Boolean(errors[`${fieldsPrefix}-country_region`]),
            }}
          />
        </div>
      </div>
    );
  }
}

CountryRegionForm.propTypes = {
  fieldsPrefix: PropTypes.string.isRequired,
  renderCondition: PropTypes.bool,
  updateForm: PropTypes.func.isRequired,
  data: PropTypes.shape({
    geoAreaType: PropTypes.string,
    geographicalAreaGroup: PropTypes.oneOfType([
      PropTypes.oneOf([""]),
      PropTypes.number,
    ]),
    ergaOmnesExclusions: PropTypes.arrayOf(PropTypes.number),
    geoGroupExclusions: PropTypes.arrayOf(PropTypes.number),
    countryRegions: PropTypes.arrayOf(PropTypes.number),
  }).isRequired,
  errors: PropTypes.objectOf(PropTypes.string).isRequired,
  countryRegionsInitial: PropTypes.arrayOf(PropTypes.number),
  countryRegionsOptions: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.number]),
    }),
  ).isRequired,
};

export { CountryRegionForm };
