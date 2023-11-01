import React from 'react';
import { DateField, Fieldset, Select } from 'govuk-react'

function QuotaOriginForm({ origin, options, index }) {
    return (
        <div>
            <h3 class="govuk-heading-m">Origin {index + 1}</h3>
            <div class="govuk-form-group">
                <Fieldset.Legend size="S">
                    Start date
                </Fieldset.Legend>
                <DateField
                    input={{
                        onBlur: function noRefCheck() { },
                        onChange: function noRefCheck() { },
                        onFocus: function noRefCheck() { }
                    }}
                    inputNames={{
                        day: `origin_${index}_start_date_0`,
                        month: `origin_${index}_start_date_1`,
                        year: `origin_${index}_start_date_2`,
                    }}
                    defaultValues={{
                        day: origin.start_date_0,
                        month: origin.start_date_1,
                        year: origin.start_date_2,
                    }}
                >
                </DateField>
            </div>
            <div class="govuk-form-group">
                <Fieldset.Legend size="S">
                    End date
                </Fieldset.Legend>
                <DateField
                    input={{
                        onBlur: function noRefCheck() { },
                        onChange: function noRefCheck() { },
                        onFocus: function noRefCheck() { }
                    }}
                    inputNames={{
                        day: `origin_${index}_end_date_0`,
                        month: `origin_${index}_end_date_1`,
                        year: `origin_${index}_end_date_2`,
                    }}
                    defaultValues={{
                        day: origin.end_date_0,
                        month: origin.end_date_1,
                        year: origin.end_date_2,
                    }}
                    hintText="Leave empty if a quota order number origin is needed for an unlimited time"
                >
                </DateField>
            </div>
            <div class="govuk-form-group">
                <Fieldset.Legend size="S">
                    Geographical area
                </Fieldset.Legend>
                <select
                    class="govuk-select"
                    name={`origin_${index}_geographical_area`}
                    defaultValue={origin.geo_area_pk}
                >
                    {options.map(geoArea =>
                        <option key={geoArea.pk} value={geoArea.value}>{geoArea.name}</option>
                    )}
                </select>
            </div>
            <hr class="govuk-!-margin-top-3" />
        </div>)
}

export { QuotaOriginForm }