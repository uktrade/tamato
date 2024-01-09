import React from 'react';
import { DateField, Fieldset, Select } from 'govuk-react'
import { QuotaOriginExclusionFormset } from './QuotaOriginExclusionFormset'
import { DeleteButton } from './DeleteButton'


function QuotaOriginForm({ origin, options, index, removeOrigin, addEmptyExclusion, removeExclusion, errors }) {

    return (
        <div>
            <h3 className="govuk-heading-m">Origin {index + 1}</h3>
            <div className="govuk-form-group">
                <DateField
                    input={{
                        onBlur: function noRefCheck() { },
                        onChange: function noRefCheck() { },
                        onFocus: function noRefCheck() { }
                    }}
                    inputNames={{
                        day: `origins-${index}-start_date_0`,
                        month: `origins-${index}-start_date_1`,
                        year: `origins-${index}-start_date_2`,
                    }}
                    defaultValues={{
                        day: origin.start_date_0,
                        month: origin.start_date_1,
                        year: origin.start_date_2,
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
                        onChange: function noRefCheck() { },
                        onFocus: function noRefCheck() { }
                    }}
                    inputNames={{
                        day: `origins-${index}-end_date_0`,
                        month: `origins-${index}-end_date_1`,
                        year: `origins-${index}-end_date_2`,
                    }}
                    defaultValues={{
                        day: origin.end_date_0,
                        month: origin.end_date_1,
                        year: origin.end_date_2,
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
                        onChange: function noRefCheck() { },
                        defaultValue: origin.geographical_area
                    }}
                    label="Geographical area"
                    defaultValue={origin.geographical_area}
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
                <QuotaOriginExclusionFormset options={options} origin={origin} errors={errors} addEmptyExclusion={addEmptyExclusion} removeExclusion={removeExclusion} />
            </div>
            <DeleteButton index={index} name={"origin"} func={removeOrigin} item={origin} parent={null} />
            <hr className="govuk-!-margin-top-3" />
        </div>)
}

export { QuotaOriginForm }