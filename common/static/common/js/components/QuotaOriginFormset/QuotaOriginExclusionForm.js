import React from 'react';
import { Select } from 'govuk-react'
import { DeleteButton } from './DeleteButton'


function QuotaOriginExclusionForm({ exclusion, origin, options, index, removeExclusion, errors }) {

    return (
        <div>
            <h3 className="govuk-heading-m">Exclusion {index + 1}</h3>
            <div className="govuk-form-group">
                <Select
                    input={{
                        name: `exclusions-${index}-geographical_area`,
                        onChange: function noRefCheck() { },
                        defaultValue: exclusion
                    }}
                    label="Geographical area"
                    defaultValue={exclusion}
                    meta={{
                        error: errors[`exclusions-${index}-geographical_area`],
                        touched: Boolean(errors[`exclusions-${index}-geographical_area`])
                    }}
                >
                    {options.map(geoArea =>
                        <option key={geoArea.value} value={geoArea.value}>{geoArea.name}</option>
                    )}
                </Select>
            </div>
            <div className="govuk-form-group">
                <DeleteButton index={index} name={"exclusion"} func={removeExclusion} item={exclusion} parent={origin} />
            </div>
        </div>)
}

export { QuotaOriginExclusionForm }