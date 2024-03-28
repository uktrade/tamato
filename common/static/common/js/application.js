/* global require:readonly */
const images = require.context(
  "../../../../node_modules/govuk-frontend/govuk/assets/images",
  true
);

/* eslint-disable */
const imagePath = (name) => images(name, true);
/* eslint-enable */

require.context("govuk-frontend/govuk/assets");

import { initAll } from "govuk-frontend";

import showHideCheckboxes from "./showHideCheckboxes";
import { initAutocomplete } from "./autocomplete";
import { initAutocompleteProgressiveEnhancement } from "./autocompleteProgressiveEnhancement";
import { initAddNewEnhancement } from "./addNewForm";
import { initCopyToNextDuties } from "./copyDuties";
import initCheckboxes from "./checkboxes";
import initConditionalMeasureConditions from "./conditionalMeasureConditions";
import initFilterDisabledToggleForComCode from "./conditionalDisablingFilters";
import initOpenCloseAccordionSection from "./openCloseAccordion";
import initTapDebounce from "./buttonDebounce";
import { setupQuotaOriginFormset } from "./components/QuotaOriginFormset/index";
import { setupWorkbasketUserAssignment } from "./components/WorkbasketUserAssignment/index";

showHideCheckboxes();
// Initialise accessible-autocomplete components without a `name` attr in order
// to avoid the "dummy" autocomplete field being submitted as part of the form
// to the server.
initAll();
initAddNewEnhancement();
initAutocomplete(false);
initCopyToNextDuties();
initCheckboxes();
initConditionalMeasureConditions();
initAutocompleteProgressiveEnhancement();
initFilterDisabledToggleForComCode();
initOpenCloseAccordionSection();
initTapDebounce();
setupQuotaOriginFormset();
setupWorkbasketUserAssignment();
