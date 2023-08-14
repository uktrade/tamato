// conditionally disables a filter based on the condition of another filter

const setFilterDisabledToggle = () => {
    document.addEventListener('DOMContentLoaded', function() {
        let specificCommodityCode = document.getElementById('goods_nomenclature_autocomplete');
        let includeInheritedMeasures = document.getElementById('id_modc');

        includeInheritedMeasures.disabled = true;

        specificCommodityCode.addEventListener('change', function() {
            if (this.value) {
                includeInheritedMeasures.disabled = false;
            } else {
                includeInheritedMeasures.disabled = this.textContentrue
            }
        })
    })
}

export default setFilterDisabledToggle