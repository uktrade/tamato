const images = require.context('../../../../node_modules/govuk-frontend/govuk/assets/images', true)
const imagePath = (name) => images(name, true)

require.context('govuk-frontend/govuk/assets');
import showHideCheckboxes from './showHideCheckboxes';
import initAutocomplete from './autocomplete';
import { initAll } from 'govuk-frontend';
showHideCheckboxes();
initAutocomplete();
initAll();
