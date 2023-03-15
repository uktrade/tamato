const images = require.context('../../../../node_modules/govuk-frontend/govuk/assets/images', true)
const imagePath = (name) => images(name, true)

require.context('govuk-frontend/govuk/assets');
import showHideCheckboxes from './showHideCheckboxes';
import { initAutocomplete } from './autocomplete';
import { initAddNewEnhancement } from './addNewForm';
import { initCopyToNextDuties } from './copyDuties';
import initStepNav from './step-by-step-nav';
import { initAll } from 'govuk-frontend';
import initCheckboxes from './checkboxes';
import initConditionalMeasureConditions from './conditionalMeasureConditions';
showHideCheckboxes();
// Initialise accessible-autocomplete components without a `name` attr in order
// to avoid the "dummy" autocomplete field being submitted as part of the form
// to the server.
initAddNewEnhancement();
initAutocomplete(false);
initCopyToNextDuties();
initStepNav();
initAll();
initCheckboxes();
initConditionalMeasureConditions();
