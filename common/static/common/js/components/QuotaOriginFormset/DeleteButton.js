import React from "react";
import PropTypes from "prop-types";

function DeleteButton({ renderCondition, name, func, item, parent }) {
  if (renderCondition) {
    return (
      <button
        onClick={func.bind(this, item, parent)}
        className="govuk-button govuk-button--secondary"
      >
        Delete this {name}
      </button>
    );
  }
}
DeleteButton.propTypes = {
  renderCondition: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired,
  func: PropTypes.func.isRequired,
  item: PropTypes.object.isRequired,
  parent: PropTypes.object,
};

export { DeleteButton };
