import { useState } from 'react';
import React from 'react';
import { DateField, Fieldset, Select } from 'govuk-react'
import { DeleteButton } from './DeleteButton'


function QuotaOriginExclusionForm({ exclusion, options, index, removeExclusion, errors }) {
    const [data, setData] = useState({ ...exclusion });

    return (
        <div>
            <h3 className="govuk-heading-m">Exclusion {index + 1}</h3>
            <div className="govuk-form-group">
                <Select
                    input={{
                        name: `exclusions-${index}-geographical_area`,
                        onChange: setData.bind(this, { ...data }),
                        defaultValue: data
                    }}
                    label="Geographical area"
                    defaultValue={data}
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
                <DeleteButton index={index} name={"exclusion"} func={removeExclusion} item={data} />
            </div>
        </div>)
}

export { QuotaOriginExclusionForm }