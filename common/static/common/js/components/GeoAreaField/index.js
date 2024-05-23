import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import PropTypes from "prop-types";

import { GeoGroupForm } from "./GeoGroupForm";
import { CountryRegionForm } from "./CountryRegionForm";
import { ErgaOmnesForm } from "./ErgaOmnesForm";

function GeoAreaField({
  initial,
  exclusionsOptions,
  groupsOptions,
  countryRegionsOptions,
  groupsWithMembers,
}) {
  const fieldName = "geographical_area-geo_area";
  const fieldsPrefix = "geographical_area";
  const [geoArea, setGeoArea] = useState(initial.geoAreaType);

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

  return (
    <>
      <input type="hidden" name="react" value={true} />
      <div className="govuk-radios">
        <div className="govuk-radios__item">
          <input
            className="govuk-radios__input"
            id="erga_omnes"
            name={fieldName}
            checked={geoArea == "ERGA_OMNES"}
            onChange={(e) => {
              setGeoArea(e.target.value);
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
          renderCondition={geoArea == "ERGA_OMNES"}
          ergaOmnesExclusionsInitial={ergaOmnesExclusionsInitial}
          exclusionsOptions={exclusionsOptions}
        />
        <div className="govuk-radios__item">
          <input
            className="govuk-radios__input"
            id="group"
            name={fieldName}
            checked={geoArea == "GROUP"}
            onChange={(e) => {
              setGeoArea(e.target.value);
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
          renderCondition={geoArea == "GROUP"}
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
            checked={geoArea == "COUNTRY"}
            onChange={(e) => {
              setGeoArea(e.target.value);
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
          renderCondition={geoArea == "COUNTRY"}
          countryRegionsInitial={countryRegionsInitial}
          countryRegionsOptions={countryRegionsOptions}
        />
      </div>
    </>
  );
}

function init() {
  const container = document.getElementById("geo-area-form-field");
  if (!container) return;
  const root = createRoot(container);
  /* eslint-disable */
  // initial, exclusionsOptions, groupsOptions, countryRegionsOptions, groupsWithMembers come from template measures/jinja2/includes/measures/geo_area_script.jinja and MeasureGeographicalAreaForm.init_layout
  root.render(
    <GeoAreaField
      initial={initial}
      exclusionsOptions={exclusionsOptions}
      groupsOptions={groupsOptions}
      countryRegionsOptions={countryRegionsOptions}
      groupsWithMembers={groupsWithMembers}
    />,
  );
  /* eslint-enable */
}

function setupGeoAreaField() {
  document.addEventListener("DOMContentLoaded", init());
}

GeoAreaField.propTypes = {
  initial: PropTypes.shape({
    geoAreaType: PropTypes.string,
    geographicalAreaGroup: PropTypes.number,
    ergaOmnesExclusions: PropTypes.arrayOf(PropTypes.number),
    geoGroupExclusions: PropTypes.arrayOf(PropTypes.number),
    countryRegions: PropTypes.arrayOf(PropTypes.number),
  }).isRequired,
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
  countryRegionsOptions: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.number.isRequired,
    }),
  ).isRequired,
  groupsWithMembers: PropTypes.objectOf(PropTypes.number),
};

export { setupGeoAreaField, GeoAreaField };
