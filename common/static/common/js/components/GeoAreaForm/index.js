import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import PropTypes from "prop-types";

import { GeoAreaField } from "./GeoAreaField";
import { SubmitButton } from "../SubmitButton";
import { ErrorSummary } from "../ErrorSummary";

function GeoAreaForm({
  initial,
  errors,
  csrfToken,
  helpText,
  ergaOmnesExclusions,
  groupsOptions,
  countryRegionsOptions,
  groupsWithMembers,
}) {
  const fieldPrefix = "geographical_area";
  const wizardStepFieldName = "measure_create_wizard-current_step";
  const wizardStepFieldId = "id_measure_create_wizard-current_step";
  const wizardStep = "geographical_area";
  const errorClass = Object.values(errors).length
    ? "govuk-form-group--error"
    : "";
  const [data, setData] = useState({ ...initial });

  function updateForm(name, value) {
    if (typeof name == "string") {
      setData({ ...data, [name]: value });
    } else {
      // allow updating of multiple keys at once since we can't do two setStates in the same interaction
      const newData = {};
      name.forEach((key, i) => {
        newData[key] = value[i];
      });
      setData({ ...data, ...newData });
    }
  }

  return (
    <>
      <form>
        <ErrorSummary errors={errors} />
        <div className={`govuk-form-group ${errorClass}`}>
          <div id="id_geographical_area-geo_area_hint" className="govuk-hint">
            {helpText}
          </div>
          <GeoAreaField
            initial={initial}
            errors={errors}
            data={data}
            updateForm={updateForm}
            ergaOmnesExclusions={ergaOmnesExclusions}
            exclusionsOptions={countryRegionsOptions}
            groupsOptions={groupsOptions}
            countryRegionsOptions={countryRegionsOptions}
            groupsWithMembers={groupsWithMembers}
          />
        </div>
      </form>
      <form method="post">
        {/* use this invisible form to submit data in the format django is expecting so we can reuse existing validation */}
        <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
        <input
          type="hidden"
          name={wizardStepFieldName}
          value={wizardStep}
          id={wizardStepFieldId}
        />
        <input
          type="hidden"
          name={`${fieldPrefix}-geo_area`}
          value={data.geoAreaType}
        />
        <input
          type="hidden"
          name={`${fieldPrefix}-geographical_area_group`}
          value={data.geographicalAreaGroup.value}
        />
        {data.ergaOmnesExclusions.map((exclusion, i) => (
          <input
            type="hidden"
            name={`erga_omnes_exclusions_formset-${i}-erga_omnes_exclusion`}
            value={exclusion.value}
            key={exclusion.value}
          />
        ))}
        {data.geoGroupExclusions.map((exclusion, i) => (
          <input
            type="hidden"
            name={`geo_group_exclusions_formset-${i}-geo_group_exclusion`}
            value={exclusion.value}
            key={exclusion.value}
          />
        ))}
        {data.countryRegions.map((country, i) => (
          <input
            type="hidden"
            name={`country_region_formset-${i}-geographical_area_country_or_region`}
            value={country.value}
            key={country.value}
          />
        ))}
        <SubmitButton buttonText="Continue" />
      </form>
    </>
  );
}

function init() {
  const csrfToken = document.querySelector(
    "input[name=csrfmiddlewaretoken]",
  ).value;
  const helpText = document.querySelector(
    "#id_geographical_area-geo_area_hint",
  )?.innerHTML;
  const container = document.querySelector("#measure-wizard-form-container");
  if (!container) return;
  const root = createRoot(container);
  /* eslint-disable */
  // initial, geoAreaErrors, ergaOmnesExclusions, groupsOptions, countryRegionsOptions, groupsWithMembers come from template measures/jinja2/includes/measures/geo_area_script.jinja and MeasureGeographicalAreaForm.init_layout
  root.render(
    <GeoAreaForm
      initial={initial}
      errors={geoAreaErrors}
      csrfToken={csrfToken}
      helpText={helpText}
      ergaOmnesExclusions={ergaOmnesExclusions}
      groupsOptions={groupsOptions}
      countryRegionsOptions={countryRegionsOptions}
      groupsWithMembers={groupsWithMembers}
    />,
  );
  /* eslint-enable */
}

function setupGeoAreaForm() {
  document.addEventListener("DOMContentLoaded", init());
}

GeoAreaForm.propTypes = {
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
  csrfToken: PropTypes.string.isRequired,
  helpText: PropTypes.string.isRequired,
  ergaOmnesExclusions: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.number.isRequired,
    }),
  ).isRequired,
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
  groupsWithMembers: PropTypes.objectOf(PropTypes.arrayOf(PropTypes.number)),
};

export { setupGeoAreaForm, GeoAreaField, GeoAreaForm };
