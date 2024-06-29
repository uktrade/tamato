import React from "react";
import PropTypes from "prop-types";

function ErrorSummary({ errors }) {
  if (Object.values(errors).length > 0) {
    return (
      <div
        className="govuk-error-summary"
        aria-labelledby="error-summary-title"
        role="alert"
        tabIndex="-1"
        data-module="govuk-error-summary"
      >
        <h2 className="govuk-error-summary__title" id="error-summary-title">
          There is a problem
        </h2>
        <div className="govuk-error-summary__body">
          <ul className="govuk-list govuk-error-summary__list">
            {Object.keys(errors).map((key) => (
              <li key={key}>
                <a href={`#${key}`}>{errors[key]}</a>
              </li>
            ))}
          </ul>
        </div>
      </div>
    );
  }
}

ErrorSummary.propTypes = {
  errors: PropTypes.objectOf(PropTypes.string).isRequired,
};

export { ErrorSummary };
