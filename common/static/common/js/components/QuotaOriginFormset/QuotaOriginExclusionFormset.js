import React from 'react';
import { QuotaOriginExclusionForm } from './QuotaOriginExclusionForm'


function QuotaOriginExclusionFormset({ origin, options, errors, addEmptyExclusion, removeExclusion }) {

    return (
        <div className="govuk-inset-text" aria-live="polite">
            {origin.exclusions.map((exclusion, i) =>
                <QuotaOriginExclusionForm exclusion={exclusion} origin={origin} key={exclusion.id} options={options} index={i} removeExclusion={removeExclusion} errors={errors} />
            )}
            <button onClick={addEmptyExclusion.bind(this, origin)} className="govuk-button govuk-button--secondary">Add an exclusion</button>
        </div>
    )
}

export { QuotaOriginExclusionFormset }