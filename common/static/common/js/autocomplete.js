import accessibleAutocomplete from 'accessible-autocomplete'

const getAdditionalCodeResults = (query, populateResults) => {
    return fetch(`/api/additional_codes/?search=${query}&format=json`)
    .then(response => response.json())
    .then(data => populateResults(data.results.map(result => ({value: result.id, string: `${result.type.sid}${result.code} - ${result.descriptions[0].description}`}))));
}

const getMeasureTypeResults = (query, populateResults) => {
    return fetch(`/api/measure_types/?search=${query}&format=json`)
    .then(response => response.json())
    .then(data => populateResults(data.results.map(result =>({value: result.id, string: `${result.sid} - ${result.description}`}))));
}

const getCommodityCodeResults = (query, populateResults) => {
    return fetch(`/api/goods_nomenclature/?search=${query}&format=json`)
    .then(response => response.json())
    .then(data => populateResults(data.results.map(result => ({value: result.id, string: `${result.item_id} - ${result.descriptions[0].description}`}))));
}

const getOrderNumberResults = (query, populateResults) => {
    return fetch(`/api/quota_order_numbers/?search=${query}&format=json`)
    .then(response => response.json())
    .then(data => populateResults(data.results.map(result => ({value: result.id, string:`${result.order_number}`}))));
}

const getRegulationResults = (query, populateResults) => {
    return fetch(`/api/regulations/?search=${query}&format=json`)
    .then(response => response.json())
    .then(data => populateResults(data.results.map(result => ({value: result.id, string: `${result.regulation_id} - ${result.information_text}`}))));
}


const getResults = {
    "AdditionalCode": getAdditionalCodeResults,
    "MeasureType": getMeasureTypeResults,
    "GoodsNomenclature": getCommodityCodeResults,
    "OrderNumber": getOrderNumberResults,
    "GeneratingRegulation": getRegulationResults,
}

const template = (result) => result && result.string

const createAutocomplete = (elementName) => { 
    let camelcaseElement = elementName.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`).substring(1);
    let element = document.querySelector(`#${camelcaseElement}_view_container`);
    let realInput = document.querySelector(`#${camelcaseElement}`)
    if (element) {
        accessibleAutocomplete({
            element: element,
            id: `${camelcaseElement}_autocomplete`,
            source: getResults[elementName],
            defaultValue: element.dataset.originalValue,
            name: `${camelcaseElement}`, 
            templates: {
                inputValue: template,
                suggestion: template
              },
            onConfirm: (val) => {
                let autoCompleteElement = document.querySelector(`#${camelcaseElement}_autocomplete`)
                if (val)
                    return realInput.value = val.value
                if (!autoCompleteElement.value) 
                    return realInput.value = ""
            },
        })
    }
}

const initAutocomplete = () => { 
    const elements = ['AdditionalCode', 'MeasureType', 'GoodsNomenclature', 'OrderNumber', 'GeneratingRegulation']
    elements.forEach((element) => createAutocomplete(element))
}

export default initAutocomplete;