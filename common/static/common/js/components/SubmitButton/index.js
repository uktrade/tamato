import React from "react";
import PropTypes from "prop-types";

function SubmitButton({ buttonText }) {
  return (
    <button className="govuk-button" id="submit-id-submit">
      {buttonText}
    </button>
  );
}

SubmitButton.propTypes = {
  buttonText: PropTypes.string.isRequired,
};

export { SubmitButton };
