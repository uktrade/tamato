/* global originsData:readonly, geoAreasOptions:readonly, originsErrors:readonly */

import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import PropTypes from "prop-types";

import { QuotaOriginForm } from "./QuotaOriginForm";

function QuotaOriginFormset({
  data,
  geoAreasOptions,
  exclusionsOptions,
  groupsWithMembers,
  errors,
}) {
  const emptyOrigin = {
    id: "",
    pk: "",
    exclusions: [],
    geographical_area: "",
    start_date_0: "",
    start_date_1: "",
    start_date_2: "",
    end_date_0: "",
    end_date_1: "",
    end_date_2: "",
  };
  if (data.length == 0) {
    data.push(emptyOrigin);
  }
  const [origins, setOrigins] = useState([...data]);

  const addEmptyOrigin = (e) => {
    e.preventDefault();
    const newEmptyOrigin = { ...emptyOrigin };
    newEmptyOrigin.id = Date.now();
    setOrigins([...origins, { ...newEmptyOrigin }]);
  };

  function removeOrigin(origin, _, e) {
    e.preventDefault();
    const newOrigins = [...origins];
    const index = origins.indexOf(origin);
    if (index > -1) {
      newOrigins.splice(index, 1);
      setOrigins(newOrigins);
    }
  }

  function updateExclusions(origin, updatedExclusions) {
    const newOrigin = { ...origin };
    let newExclusions = [];
    updatedExclusions.forEach((exclusion) => {
      newExclusions.push(exclusion.value);
    });
    newOrigin.exclusions = newExclusions;
    const newOrigins = [...origins];
    const index = newOrigins.indexOf(origin);
    if (index > -1) {
      newOrigins.splice(index, 1, newOrigin);
      setOrigins(newOrigins);
    }
  }

  function updateOrigin(origin, geoArea) {
    const newOrigins = [...origins];
    const newOrigin = { ...origin };
    newOrigin.geographical_area = Number(geoArea);
    newOrigin.exclusions = [];
    const index = origins.indexOf(origin);
    if (index > -1) {
      newOrigins.splice(index, 1, newOrigin);
      setOrigins(newOrigins);
    }
  }

  return (
    <div aria-live="polite">
      {origins.map((origin, i) => (
        <QuotaOriginForm
          origin={origin}
          key={i}
          geoAreasOptions={geoAreasOptions}
          exclusionsOptions={exclusionsOptions}
          groupsWithMembers={groupsWithMembers}
          index={i}
          updateOrigin={updateOrigin}
          removeOrigin={removeOrigin}
          updateExclusions={updateExclusions}
          errors={errors}
        />
      ))}
      <button
        onClick={addEmptyOrigin.bind(this)}
        className="govuk-button govuk-button--secondary"
      >
        Add another origin
      </button>
    </div>
  );
}
QuotaOriginFormset.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      pk: PropTypes.number.isRequired,
      exclusions: PropTypes.arrayOf(
        PropTypes.oneOfType([PropTypes.oneOf([""]), PropTypes.number]),
      ),
      geographical_area: PropTypes.number.isRequired,
      start_date_0: PropTypes.number.isRequired,
      start_date_1: PropTypes.number.isRequired,
      start_date_2: PropTypes.number.isRequired,
      end_date_0: PropTypes.oneOfType([
        PropTypes.oneOf([""]),
        PropTypes.number,
      ]),
      end_date_1: PropTypes.oneOfType([
        PropTypes.oneOf([""]),
        PropTypes.number,
      ]),
      end_date_2: PropTypes.oneOfType([
        PropTypes.oneOf([""]),
        PropTypes.number,
      ]),
    }),
  ),
  geoAreasOptions: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      value: PropTypes.number.isRequired,
    }),
  ).isRequired,
  exclusionsOptions: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.number.isRequired,
    }),
  ).isRequired,
  groupsWithMembers: PropTypes.objectOf(PropTypes.arrayOf(PropTypes.number)),
  errors: PropTypes.object,
};

function init() {
  const originsContainer = document.getElementById("quota_origins");
  if (!originsContainer) return;
  const root = createRoot(originsContainer);
  const origins = [...originsData];
  /* eslint-disable */
  // originsData, geoAreasOptions, exclusionsOptions, groupsWithMembers come from template quotas/jinja2/includes/quotas/quota-edit-origins.jinja
  // originsErrors are errors raised by django. see template quotas/jinja2/includes/quotas/quota-edit-origins.jinja
  root.render(
    <QuotaOriginFormset
      data={origins}
      geoAreasOptions={geoAreasOptions}
      exclusionsOptions={exclusionsOptions}
      groupsWithMembers={groupsWithMembers}
      errors={originsErrors}
    />,
  );
  /* eslint-enable */
}

function setupQuotaOriginFormset() {
  document.addEventListener("DOMContentLoaded", init());
}

export { setupQuotaOriginFormset, QuotaOriginFormset };
