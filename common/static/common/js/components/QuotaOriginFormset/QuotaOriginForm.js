import React, { useState } from "react";
import { DateField, Fieldset, Select } from "govuk-react";
import PropTypes from "prop-types";
import ReactSelect from "react-select";

import { DeleteButton } from "./DeleteButton";

function QuotaOriginForm({
  origin,
  geoAreasOptions,
  exclusionsOptions,
  groupsWithMembers,
  index,
  updateOrigin,
  removeOrigin,
  updateExclusions,
  errors,
}) {
  // If the form is submitted with no exclusions and fails validation
  // the exclusions key will not exist on the origin so create it here
  origin.exclusions = origin.exclusions || [];

  const exclusionsFormValue = exclusionsOptions.filter(
    (option) => origin.exclusions.indexOf(option.value) >= 0,
  );

  const [usableExclusionsOptions, setExclusionsOptions] = useState([
    ...exclusionsOptions,
  ]);

  const geoAreaIsGroup = groupsWithMembers[origin.geographical_area]
    ? true
    : false;

  function handleGeoAreaChange(origin, e) {
    if (groupsWithMembers[e.target.value]) {
      const newExclusions = exclusionsOptions.filter(
        (option) =>
          groupsWithMembers[e.target.value].indexOf(option.value) >= 0,
      );
      setExclusionsOptions(newExclusions);
    }
    // the previously selected exclusion will need to be cleared because it may not be valid
    updateOrigin(origin, e.target.value);
  }

  function exclusionsSelect() {
    if (origin.geographical_area && geoAreaIsGroup) {
      return (
        <div className="govuk-form-group">
          <div className="govuk-hint">
            Select one or more countries to be excluded:
          </div>
          <ReactSelect
            className="react-select-container"
            classNamePrefix="react-select"
            value={exclusionsFormValue}
            options={usableExclusionsOptions}
            onChange={(e) => updateExclusions(origin, e)}
            isMulti={true}
            name={`origin-exclusions`}
          />
        </div>
      );
    }
  }

  return (
    <div>
      <h3 className="govuk-heading-m">Quota origin {index + 1}</h3>
      <input type="hidden" name={`origins-${index}-pk`} value={origin.pk} />
      <div className="govuk-form-group">
        <DateField
          input={{
            onBlur: function noRefCheck() {},
            onChange: function noRefCheck() {},
            onFocus: function noRefCheck() {},
          }}
          inputNames={{
            day: `origins-${index}-start_date_0`,
            month: `origins-${index}-start_date_1`,
            year: `origins-${index}-start_date_2`,
          }}
          defaultValues={{
            day: origin.start_date_0,
            month: origin.start_date_1,
            year: origin.start_date_2,
          }}
          errorText={errors[`origins-${index}-start_date`]}
        >
          <Fieldset.Legend size="S">Start date</Fieldset.Legend>
        </DateField>
      </div>
      <div className="govuk-form-group">
        <DateField
          input={{
            onBlur: function noRefCheck() {},
            onChange: function noRefCheck() {},
            onFocus: function noRefCheck() {},
          }}
          inputNames={{
            day: `origins-${index}-end_date_0`,
            month: `origins-${index}-end_date_1`,
            year: `origins-${index}-end_date_2`,
          }}
          defaultValues={{
            day: origin.end_date_0,
            month: origin.end_date_1,
            year: origin.end_date_2,
          }}
          errorText={errors[`origins-${index}-end_date`]}
          hintText="Leave empty if a quota order number origin is needed for an unlimited time"
        >
          <Fieldset.Legend size="S">End date</Fieldset.Legend>
        </DateField>
      </div>
      <div className="govuk-form-group">
        <Fieldset.Legend size="S">Geographical area</Fieldset.Legend>
        <Select
          input={{
            name: `origins-${index}-geographical_area`,
            onChange: (value) => handleGeoAreaChange(origin, value),
            defaultValue: origin.geographical_area,
          }}
          defaultValue={origin.geographical_area}
          meta={{
            error: errors[`origins-${index}-geographical_area`],
            touched: Boolean(errors[`origins-${index}-geographical_area`]),
          }}
        >
          {geoAreasOptions.map((geoArea) => (
            <option key={geoArea.value} value={geoArea.value}>
              {geoArea.label}
            </option>
          ))}
        </Select>
      </div>
      {exclusionsSelect()}
      <DeleteButton
        renderCondition={index > 0}
        name={"origin"}
        func={removeOrigin}
        item={origin}
        parent={null}
      />
      {origin.exclusions.map((exclusion, i) => (
        <div key={i}>
          <input
            type="hidden"
            name={`origins-${index}-exclusions-${i}-pk`}
            value={exclusion.pk}
          />
          <input
            type="hidden"
            name={`origins-${index}-exclusions-${i}-geographical_area`}
            value={exclusion}
            key={exclusion.id}
          />
        </div>
      ))}
      <hr className="govuk-!-margin-top-3" />
    </div>
  );
}

QuotaOriginForm.propTypes = {
  origin: PropTypes.shape({
    id: PropTypes.number.isRequired,
    pk: PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.number]),
    exclusions: PropTypes.arrayOf(
      PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.number]),
    ),
    geographical_area: PropTypes.oneOfType([
      PropTypes.oneOf([""]),
      PropTypes.number,
    ]),
    start_date_0: PropTypes.oneOfType([
      PropTypes.oneOf([""]),
      PropTypes.number,
    ]),
    start_date_1: PropTypes.oneOfType([
      PropTypes.oneOf([""]),
      PropTypes.number,
    ]),
    start_date_2: PropTypes.oneOfType([
      PropTypes.oneOf([""]),
      PropTypes.number,
    ]),
    end_date_0: PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.number]),
    end_date_1: PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.number]),
    end_date_2: PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.number]),
  }).isRequired,
  exclusionsOptions: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.string]),
      value: PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.number]),
    }),
  ),
  geoAreasOptions: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.string]),
      value: PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.number]),
    }),
  ),
  updateExclusions: PropTypes.func.isRequired,
  updateOrigin: PropTypes.func.isRequired,
  groupsWithMembers: PropTypes.objectOf(PropTypes.arrayOf(PropTypes.number)),
  index: PropTypes.number.isRequired,
  removeOrigin: PropTypes.func.isRequired,
  errors: PropTypes.object,
};

export { QuotaOriginForm };
