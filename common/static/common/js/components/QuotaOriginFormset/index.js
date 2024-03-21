/* global originsData:readonly, geoAreasOptions:readonly, originsErrors:readonly */

import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import PropTypes from "prop-types";

import { QuotaOriginForm } from "./QuotaOriginForm";

function QuotaOriginFormset({ data, options, errors }) {
  const [origins, setOrigins] = useState([...data]);
  const emptyOrigin = {
    id: "",
    pk: "",
    exclusions: [],
    geo_area_name: "",
    geo_area_pk: "",
    start_date_0: "",
    start_date_1: "",
    start_date_2: "",
    end_date_0: "",
    end_date_1: "",
    end_date_2: "",
  };
  const emptyExclusion = {
    id: "",
    pk: "",
  };

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

  function addEmptyExclusion(origin, e) {
    e.preventDefault();
    // find parent origin and update exclusions
    const updatedOrigin = { ...origin };
    const newEmptyExclusion = { ...emptyExclusion };
    newEmptyExclusion.id = Date.now();
    const newExclusions = [...updatedOrigin.exclusions, newEmptyExclusion];
    updatedOrigin.exclusions = newExclusions;

    // update origins
    const updatedOrigins = [...origins];
    const index = origins.findIndex((o) => o.id === origin.id);
    if (index > -1) {
      updatedOrigins.splice(index, 1, updatedOrigin);
      setOrigins(updatedOrigins);
    }
  }

  function removeExclusion(exclusion, origin, e) {
    e.preventDefault();
    // remove the exclusion from its parent origin
    const newOrigin = { ...origin };
    const exclusionIndex = newOrigin.exclusions.indexOf(exclusion);
    if (exclusionIndex > -1) {
      newOrigin.exclusions.splice(exclusionIndex, 1);
    }

    // update the origin
    const newOrigins = [...origins];
    const index = newOrigins.indexOf(origin);
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
          options={options}
          index={i}
          addEmptyExclusion={addEmptyExclusion}
          removeOrigin={removeOrigin}
          removeExclusion={removeExclusion}
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
        PropTypes.shape({
          id: PropTypes.number.isRequired,
          pk: PropTypes.number.isRequired,
        }),
      ),
      geographical_area: PropTypes.number.isRequired,
      start_date_0: PropTypes.number.isRequired,
      start_date_1: PropTypes.number.isRequired,
      start_date_2: PropTypes.number.isRequired,
      end_date_0: PropTypes.number,
      end_date_1: PropTypes.number,
      end_date_2: PropTypes.number,
    }),
  ),
  options: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      value: PropTypes.number.isRequired,
    }),
  ),
  errors: PropTypes.object,
};

function init() {
  const originsContainer = document.getElementById("quota_origins");
  if (!originsContainer) return;
  const root = createRoot(originsContainer);
  const origins = [...originsData];
  // originsData and geoAreasOptions come from template quotas/jinja2/includes/quotas/quota-edit-origins.jinja
  // originsErrors are errors raised by django. see template quotas/jinja2/includes/quotas/quota-edit-origins.jinja
  root.render(
    <QuotaOriginFormset
      data={origins}
      options={geoAreasOptions}
      errors={originsErrors}
    />,
  );
}

function setupQuotaOriginFormset() {
  document.addEventListener("DOMContentLoaded", init());
}

export { setupQuotaOriginFormset, QuotaOriginFormset };
