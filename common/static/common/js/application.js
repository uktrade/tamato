const images = require.context(
  "../../../../node_modules/govuk-frontend/govuk/assets/images",
  true,
);

/* eslint-disable */
const imagePath = (name) => images(name, true);
/* eslint-enable */

require.context("govuk-frontend/govuk/assets");

import "./trustedTypes";
import { initAll } from "govuk-frontend";

import showHideCheckboxes from "./showHideCheckboxes";
import { initAutocomplete } from "./autocomplete";
import { initAutocompleteProgressiveEnhancement } from "./autocompleteProgressiveEnhancement";
import { initAddNewDefinition } from "./addNewQuotaDefinitionForm";
import { initAddNewEnhancement } from "./addNewForm";
import { initCopyToNextDuties } from "./copyDuties";
import initCheckboxes from "./checkboxes";
import initConditionalMeasureConditions from "./conditionalMeasureConditions";
import initFilterDisabledToggleForComCode from "./conditionalDisablingFilters";
import initOpenCloseAccordionSection from "./openCloseAccordion";
import initTapDebounce from "./buttonDebounce";
import { setupQuotaOriginFormset } from "./components/QuotaOriginFormset/index";
import { setupGeoAreaForm } from "./components/GeoAreaForm/index";
import { setupWorkbasketUserAssignment } from "./components/WorkbasketUserAssignment/index";
import { setupTaskUserAssignment } from "./components/TaskUserAssignment/index";
import { initMasonry } from "./masonry";

showHideCheckboxes();
// Initialise accessible-autocomplete components without a `name` attr in order
// to avoid the "dummy" autocomplete field being submitted as part of the form
// to the server.
initAll();
initAddNewDefinition();
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
setupGeoAreaForm();
setupWorkbasketUserAssignment();
setupTaskUserAssignment();
initMasonry();
