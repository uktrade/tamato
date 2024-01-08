import { useState } from 'react';
import React from 'react';
import { DateField, Fieldset, Select } from 'govuk-react'
import { QuotaOriginExclusionFormset } from './QuotaOriginExclusionFormset'
import { DeleteButton } from './DeleteButton'


function QuotaOriginForm({ origin, options, index, removeOrigin, errors }) {
    const [data, setData] = useState({ ...origin });

    return (
        <div>
            <h3 className="govuk-heading-m">Origin {index + 1}</h3>
            <div className="govuk-form-group">
                <DateField
                    input={{
                        onBlur: function noRefCheck() { },
                        onChange: setData.bind(this, { ...data }),
                        onFocus: function noRefCheck() { }
                    }}
                    inputNames={{
                        day: `origins-${index}-start_date_0`,
                        month: `origins-${index}-start_date_1`,
                        year: `origins-${index}-start_date_2`,
                    }}
                    defaultValues={{
                        day: data.start_date_0,
                        month: data.start_date_1,
                        year: data.start_date_2,
                    }}
                    errorText={errors[`origins-${index}-start_date`]}
                >
                    <Fieldset.Legend size="S">
                        Start date
                    </Fieldset.Legend>
                </DateField>
            </div>
            <div className="govuk-form-group">
                <DateField
                    input={{
                        onBlur: function noRefCheck() { },
                        onChange: setData.bind(this, { ...data }),
                        onFocus: function noRefCheck() { }
                    }}
                    inputNames={{
                        day: `origins-${index}-end_date_0`,
                        month: `origins-${index}-end_date_1`,
                        year: `origins-${index}-end_date_2`,
                    }}
                    defaultValues={{
                        day: data.end_date_0,
                        month: data.end_date_1,
                        year: data.end_date_2,
                    }}
                    errorText={errors[`origins-${index}-end_date`]}
                    hintText="Leave empty if a quota order number origin is needed for an unlimited time"
                >
                    <Fieldset.Legend size="S">
                        End date
                    </Fieldset.Legend>
                </DateField>
            </div>
            <div className="govuk-form-group">
                <Select
                    input={{
                        name: `origins-${index}-geographical_area`,
                        onChange: setData.bind(this, { ...data }),
                        defaultValue: data.geographical_area
                    }}
                    label="Geographical area"
                    defaultValue={data.geographical_area}
                    meta={{
                        error: errors[`origins-${index}-geographical_area`],
                        touched: Boolean(errors[`origins-${index}-geographical_area`])
                    }}
                >
                    {options.map(geoArea =>
                        <option key={geoArea.value} value={geoArea.value}>{geoArea.name}</option>
                    )}
                </Select>
            </div>
            <div className="govuk-form-group">
                <h4 className="govuk-heading-s">Geographical exclusions</h4>
                <QuotaOriginExclusionFormset data={data.exclusions} options={options} errors={errors} />
            </div>
            <DeleteButton index={index} name={"origin"} func={removeOrigin} item={origin} />
            <hr className="govuk-!-margin-top-3" />
        </div>)
}

export { QuotaOriginForm }