import React from 'react';


function DeleteButton({ renderCondition, name, func, item, parent }) {
    if (renderCondition) {
        return (
            <button onClick={func.bind(this, item, parent)} className="govuk-button govuk-button--secondary">Delete this {name}</button>
        )
    }
}

export { DeleteButton }