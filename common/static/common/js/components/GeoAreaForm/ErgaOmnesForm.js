import React from "react";
import PropTypes from "prop-types";
import Select from "react-select";

function ErgaOmnesForm({
  fieldsPrefix,
  renderCondition,
  updateForm,
  data,
  errors,
  ergaOmnesExclusionsInitial,
  exclusionsOptions,
}) {
  if (renderCondition) {
    return (
      <div className="govuk-radios__conditional">
        <div
          className="govuk-form-group"
          data-testid="erga_omnes_exclusions_select"
        >
          <div className="govuk-hint">
            Select one or more countries to be excluded:
          </div>
          <Select
            className="react-select-container"
            classNamePrefix="react-select"
            options={exclusionsOptions}
            defaultValue={ergaOmnesExclusionsInitial}
            value={data.ergaOmnesExclusions}
            onChange={(value) => updateForm("ergaOmnesExclusions", value)}
            isMulti={true}
            name={`${fieldsPrefix}-erga_omnes_exclusions`}
            id="erga_omnes_exclusions_select"
            meta={{
              error: errors[`${fieldsPrefix}-erga_omnes_exclusions`],
              touched: Boolean(errors[`${fieldsPrefix}-erga_omnes_exclusions`]),
            }}
          />
        </div>
      </div>
    );
  }
}

ErgaOmnesForm.propTypes = {
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
  ergaOmnesExclusionsInitial: PropTypes.arrayOf(PropTypes.number),
  exclusionsOptions: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.number]),
    }),
  ).isRequired,
};

export { ErgaOmnesForm };
