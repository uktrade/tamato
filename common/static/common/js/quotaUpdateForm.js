import { createRoot } from 'react-dom/client';
import React from 'react';
import { DateField, Fieldset } from 'govuk-react'


function setupQuotaUpdateForm() {
    const origins = document.getElementById("quota_origins");
    // console.log(categoryElement)
    const QuotaOriginForm = () => (
        <div>
            <Fieldset>
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
                        day: 'start_date_0',
                        month: 'start_date_1',
                        year: 'start_date_2',
                    }}
                >
                </DateField>
            </Fieldset>
            <Fieldset>
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
                        day: 'end_date_0',
                        month: 'end_date_1',
                        year: 'end_date_2',
                    }}
                    hintText="Leave empty if a quota order number origin is needed for an unlimited time"
                >
                </DateField>
            </Fieldset>
        </div>
    )

    const QuotaOrigins = () => (
        <QuotaOriginForm />
    )
    const root = createRoot(origins);
    root.render(<QuotaOrigins />);
}

export { setupQuotaUpdateForm };