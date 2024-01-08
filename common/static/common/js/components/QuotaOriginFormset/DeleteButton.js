import React from 'react';


function DeleteButton({ index, name, func, item }) {
    if (index > 0) {
        return (
            <button onClick={func.bind(this, item)} className="govuk-button govuk-button--secondary">Delete this {name}</button>
        )
    }
}

export { DeleteButton }