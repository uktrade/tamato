// conditionally disables modc filter based on goods_nomenclature_autocomplete filter having a value
// TODO: refactor to allow passing two widget ids: 1. widget condition is based on 2. widget to be disabled.

const initFilterDisabledToggleForComCode = () => {
    document.addEventListener('DOMContentLoaded', function() {
        let specificCommodityCode = document.getElementById('goods_nomenclature_autocomplete');
        let includeInheritedMeasures = document.getElementById('id_modc');

        if (specificCommodityCode.value) {
            includeInheritedMeasures.disabled = false;
        } else {
            includeInheritedMeasures.disabled = true;
        }

        specificCommodityCode.addEventListener('change', function() {
            if (this.value) {
                includeInheritedMeasures.disabled = false;
            } else {
                includeInheritedMeasures.disabled = true;
            }
        })
    })
}

export default initFilterDisabledToggleForComCode;