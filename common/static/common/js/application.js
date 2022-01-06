const images = require.context('../../../../node_modules/govuk-frontend/govuk/assets/images', true)
const imagePath = (name) => images(name, true)

require.context('govuk-frontend/govuk/assets');
import showHideCheckboxes from './showHideCheckboxes';
import initAutocomplete from './autocomplete';
import initStepNav from './step-by-step-nav';
import { initAll } from 'govuk-frontend';
import initCheckAllCheckboxes from './checkAllCheckboxes';
showHideCheckboxes();
initAutocomplete();
initStepNav();
initAll();
initCheckAllCheckboxes();
