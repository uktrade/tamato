import { useState } from 'react';
import React from 'react';
import { Button, DateField, Fieldset, Select } from 'govuk-react'


function QuotaOriginForm({ origin, options, index, removeOrigin }) {
    const [data, setData] = useState({ ...origin });

    return (
        <div>
            <h3 className="govuk-heading-m">Origin {index + 1}</h3>
            <div className="govuk-form-group">
                <Fieldset.Legend size="S">
                    Start date
                </Fieldset.Legend>
                <DateField
                    input={{
                        onBlur: function noRefCheck() { },
                        onChange: setData.bind(this, { ...data }),
                        onFocus: function noRefCheck() { }
                    }}
                    inputNames={{
                        day: `origins_${index}_start_date_0`,
                        month: `origins_${index}_start_date_1`,
                        year: `origins_${index}_start_date_2`,
                    }}
                    defaultValues={{
                        day: data.start_date_0,
                        month: data.start_date_1,
                        year: data.start_date_2,
                    }}
                >
                </DateField>
            </div>
            <div className="govuk-form-group">
                <Fieldset.Legend size="S">
                    End date
                </Fieldset.Legend>
                <DateField
                    input={{
                        onBlur: function noRefCheck() { },
                        onChange: setData.bind(this, { ...data }),
                        onFocus: function noRefCheck() { }
                    }}
                    inputNames={{
                        day: `origins_${index}_end_date_0`,
                        month: `origins_${index}_end_date_1`,
                        year: `origins_${index}_end_date_2`,
                    }}
                    defaultValues={{
                        day: data.end_date_0,
                        month: data.end_date_1,
                        year: data.end_date_2,
                    }}
                    hintText="Leave empty if a quota order number origin is needed for an unlimited time"
                >
                </DateField>
            </div>
            <div className="govuk-form-group">
                <Fieldset.Legend size="S">
                    Geographical area
                </Fieldset.Legend>
                <select
                    className="govuk-select"
                    name={`origins_${index}_geographical_area`}
                    defaultValue={data.geo_area_pk}
                >
                    {options.map(geoArea =>
                        <option key={geoArea.pk} value={geoArea.value}>{geoArea.name}</option>
                    )}
                </select>
            </div>
            <button onClick={removeOrigin.bind(this, origin)} className="govuk-button govuk-button--secondary">Delete</button>
            <hr className="govuk-!-margin-top-3" />
        </div>)
}

export { QuotaOriginForm }