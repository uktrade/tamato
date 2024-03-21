import React from "react";
import PropTypes from "prop-types";

import { QuotaOriginExclusionForm } from "./QuotaOriginExclusionForm";

function QuotaOriginExclusionFormset({
  origin,
  originIndex,
  options,
  errors,
  addEmptyExclusion,
  removeExclusion,
}) {
  return (
    <div className="govuk-inset-text" aria-live="polite">
      {origin.exclusions.map((exclusion, i) => (
        <QuotaOriginExclusionForm
          exclusion={exclusion}
          origin={origin}
          key={exclusion.id}
          options={options}
          index={i}
          originIndex={originIndex}
          removeExclusion={removeExclusion}
          errors={errors}
        />
      ))}
      <button
        onClick={addEmptyExclusion.bind(this, origin)}
        className="govuk-button govuk-button--secondary"
      >
        Add an exclusion
      </button>
    </div>
  );
}
QuotaOriginExclusionFormset.propTypes = {
  origin: PropTypes.shape({
    id: PropTypes.number.isRequired,
    pk: PropTypes.string.isRequired,
    exclusions: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number.isRequired,
        pk: PropTypes.string.isRequired,
      }),
    ),
    geographical_area: PropTypes.number.isRequired,
    start_date_0: PropTypes.number.isRequired,
    start_date_1: PropTypes.number.isRequired,
    start_date_2: PropTypes.number.isRequired,
    end_date_0: PropTypes.number,
    end_date_1: PropTypes.number,
    end_date_2: PropTypes.number,
  }).isRequired,
  originIndex: PropTypes.number.isRequired,
  options: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      value: PropTypes.number.isRequired,
    }),
  ),
  errors: PropTypes.object,
  addEmptyExclusion: PropTypes.func.isRequired,
  removeExclusion: PropTypes.func.isRequired,
};

export { QuotaOriginExclusionFormset };
