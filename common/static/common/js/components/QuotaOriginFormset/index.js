import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import React from 'react';
import { QuotaOriginForm } from './QuotaOriginForm'


function QuotaOriginFormset({ data, options }) {
    const [origins, setOrigins] = useState([...data]);
    const emptyOrigin = {
        "exclusions": [
        ],
        "geo_area_name": "",
        "geo_area_pk": "",
        "start_date_0": "",
        "start_date_1": "",
        "start_date_2": "",
        "end_date_0": "",
        "end_date_1": "",
        "end_date_2": "",
    }

    const addEmptyOrigin = (e) => {
        e.preventDefault();
        setOrigins([...origins, { ...emptyOrigin }]);
    }

    function removeOrigin(origin, e) {
        e.preventDefault();
        const newOrigins = [...origins]
        const index = origins.indexOf(origin)
        if (index > -1) {
            newOrigins.splice(index, 1)
            setOrigins(newOrigins)
        }
    }

    return (
        <div aria-live="polite">
            {origins.map((origin, i) =>
                <QuotaOriginForm origin={origin} options={options} index={i} removeOrigin={removeOrigin} />
            )}
            <button onClick={addEmptyOrigin.bind(this)} className="govuk-button govuk-button--secondary">Add another</button>
        </div>
    )
}

function init() {
    const originsContainer = document.getElementById("quota_origins");
    const root = createRoot(originsContainer);
    const origins = [...originsData];
    // originsData and geoAreasOptions come from template quotas/jinja2/includes/quotas/quota-edit-origins.jinja
    console.log(origins)
    root.render(
        <QuotaOriginFormset data={origins} options={geoAreasOptions} />
    );
}

function setupQuotaOriginFormset() {
    document.addEventListener('DOMContentLoaded', init())
}

export { setupQuotaOriginFormset };