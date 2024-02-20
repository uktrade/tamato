import React from 'react';
import { Select } from 'govuk-react'
import { DeleteButton } from './DeleteButton'


function QuotaOriginExclusionForm({ exclusion, origin, options, originIndex, index, removeExclusion, errors }) {

    return (
        <div>
            <h5 className="govuk-heading-s">Exclusion {index + 1}</h5>
            <div className="govuk-form-group">
                <input
                    type="hidden"
                    name={`origins-${originIndex}-exclusions-${index}-pk`}
                    value={exclusion.pk}
                />
                <Select
                    input={{
                        name: `origins-${originIndex}-exclusions-${index}-geographical_area`,
                        onChange: function noRefCheck() { },
                        defaultValue: exclusion.id
                    }}
                    label="Geographical area"
                    defaultValue={exclusion.id}
                    meta={{
                        error: errors[`origins-${originIndex}-exclusions-${index}-geographical_area`],
                        touched: Boolean(errors[`origins-${originIndex}-exclusions-${index}-geographical_area`])
                    }}
                >
                    {options.map(geoArea =>
                        <option key={geoArea.value} value={geoArea.value}>{geoArea.name}</option>
                    )}
                </Select>
            </div>
            <div className="govuk-form-group">
                <DeleteButton renderCondition={true} name={"exclusion"} func={removeExclusion} item={exclusion} parent={origin} />
            </div>
        </div>)
}

export { QuotaOriginExclusionForm }