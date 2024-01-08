import { useState } from 'react';
import React from 'react';
import { QuotaOriginExclusionForm } from './QuotaOriginExclusionForm'


function QuotaOriginExclusionFormset({ data, options, errors }) {
    const emptyExclusion = {
        "id": "",
        "pk": "",
    }
    const [exclusions, setExclusions] = useState([...data]);

    const addEmptyExclusion = (e) => {
        e.preventDefault();
        const newExclusion = { ...emptyExclusion }
        newExclusion.id = Date.now()
        setExclusions([...exclusions, { ...newExclusion }]);
    }

    function removeExclusion(exclusion, e) {
        e.preventDefault();
        const newExclusions = [...exclusions]
        const index = exclusions.indexOf(exclusion)
        if (index > -1) {
            newExclusions.splice(index, 1)
            setExclusions(newExclusions)
        }
    }

    return (
        <div className="govuk-inset-text" aria-live="polite">
            {exclusions.map((exclusion, i) =>
                <QuotaOriginExclusionForm exclusion={exclusion} key={exclusion.id} options={options} index={i} removeExclusion={removeExclusion} errors={errors} />
            )}
            <button onClick={addEmptyExclusion.bind(this)} className="govuk-button govuk-button--secondary">Add an exclusion</button>
        </div>
    )
}

export { QuotaOriginExclusionFormset }