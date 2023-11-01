import { createRoot } from 'react-dom/client';
import React from 'react';
import { QuotaOriginForm } from './QuotaOriginForm'


function init() {
    function QuotaOrigins({ data, options }) {
        return (
            <div>
                {data.map((origin, i) =>
                    <QuotaOriginForm origin={origin} options={options} index={i} />
                )}
            </div>
        )
    }
    const origins = document.getElementById("quota_origins");
    const root = createRoot(origins);
    console.log(originsData)
    root.render(<QuotaOrigins data={originsData} options={geoAreasOptions} />);
}

function setupQuotaUpdateForm() {
    document.addEventListener('DOMContentLoaded', init())
}

export { setupQuotaUpdateForm };