import React from "react";
import PropTypes from "prop-types";

import { GeoGroupForm } from "./GeoGroupForm";
import { CountryRegionForm } from "./CountryRegionForm";
import { ErgaOmnesForm } from "./ErgaOmnesForm";

function GeoAreaField({
  initial,
  errors,
  updateForm,
  data,
  exclusionsOptions,
  groupsOptions,
  countryRegionsOptions,
  groupsWithMembers,
}) {
  const fieldName = "geographical_area-geo_area";
  const fieldsPrefix = "geographical_area";

  const countryRegionsInitial = countryRegionsOptions.filter(
    (option) => initial.countryRegions.indexOf(option.value) >= 0,
  );
  const ergaOmnesExclusionsInitial = countryRegionsOptions.filter(
    (option) => initial.ergaOmnesExclusions.indexOf(option.value) >= 0,
  );
  const geoGroupInitial = groupsOptions.filter(
    (option) => option.value == initial.geographicalAreaGroup,
  )[0];
  const geoGroupExclusionsInitial = countryRegionsOptions.filter(
    (option) => initial.geoGroupExclusions.indexOf(option.value) >= 0,
  );

  function errorDisplay() {
    if (errors.geo_area) {
      return (
        <span className="govuk-error-message">
          <span className="govuk-visually-hidden">Error: </span>
          {errors.geo_area}
        </span>
      );
    }
  }

  return (
    <div className="govuk-form-group">
      <input type="hidden" name="react" value={true} />
      {errorDisplay()}
      <div className="govuk-radios">
        <div className="govuk-radios__item">
          <input
            className="govuk-radios__input"
            id="erga_omnes"
            name={fieldName}
            checked={data.geoAreaType == "ERGA_OMNES"}
            onChange={(e) => {
              updateForm("geoAreaType", e.target.value);
            }}
            type="radio"
            value="ERGA_OMNES"
          />
          <label
            className="govuk-label govuk-radios__label"
            htmlFor="erga_omnes"
          >
            All countries (erga omnes)
          </label>
        </div>
        <ErgaOmnesForm
          fieldsPrefix={fieldsPrefix}
          renderCondition={data.geoAreaType == "ERGA_OMNES"}
          updateForm={updateForm}
          data={data}
          errors={errors}
          ergaOmnesExclusionsInitial={ergaOmnesExclusionsInitial}
          exclusionsOptions={exclusionsOptions}
        />
        <div className="govuk-radios__item">
          <input
            className="govuk-radios__input"
            id="group"
            name={fieldName}
            checked={data.geoAreaType == "GROUP"}
            onChange={(e) => {
              updateForm("geoAreaType", e.target.value);
            }}
            type="radio"
            value="GROUP"
          />
          <label className="govuk-label govuk-radios__label" htmlFor="group">
            A group of countries
          </label>
        </div>
        <GeoGroupForm
          fieldsPrefix={fieldsPrefix}
          renderCondition={data.geoAreaType == "GROUP"}
          updateForm={updateForm}
          errors={errors}
          geographicalAreaGroup={data.geographicalAreaGroup}
          geoGroupExclusions={data.geoGroupExclusions}
          geoGroupInitial={geoGroupInitial}
          groupsWithMembers={groupsWithMembers}
          geoGroupExclusionsInitial={geoGroupExclusionsInitial}
          groupsOptions={groupsOptions}
          exclusionsOptions={exclusionsOptions}
        />
        <div className="govuk-radios__item">
          <input
            className="govuk-radios__input"
            id="country"
            name={fieldName}
            checked={data.geoAreaType == "COUNTRY"}
            onChange={(e) => {
              updateForm("geoAreaType", e.target.value);
            }}
            type="radio"
            value="COUNTRY"
          />
          <label className="govuk-label govuk-radios__label" htmlFor="country">
            Specific countries or regions
          </label>
        </div>
        <CountryRegionForm
          fieldsPrefix={fieldsPrefix}
          renderCondition={data.geoAreaType == "COUNTRY"}
          updateForm={updateForm}
          data={data}
          errors={errors}
          countryRegionsInitial={countryRegionsInitial}
          countryRegionsOptions={countryRegionsOptions}
        />
      </div>
    </div>
  );
}

GeoAreaField.propTypes = {
  initial: PropTypes.shape({
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
  countryRegionsOptions: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.number]),
    }),
  ).isRequired,
  groupsWithMembers: PropTypes.objectOf(PropTypes.arrayOf(PropTypes.number)),
};

export { GeoAreaField };
