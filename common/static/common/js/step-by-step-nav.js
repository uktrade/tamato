class StepNav {

  constructor(element) {
    this.element = element;
    // stores text for JS appended elements 'show' and 'hide' on steps, and 'show/hide all' button
    this.actions = {};
    this.rememberShownStep = false;
    this.stepNavSize = false;
    this.sessionStoreLink = 'govuk-step-nav-active-link';
    this.activeLinkClass = 'gem-c-step-nav__list-item--active';
    this.activeStepClass = 'gem-c-step-nav__step--active';
    this.activeLinkHref = '#content';
    this.uniqueId = false;

    // Indicate that js has worked
    this.element.classList.add('gem-c-step-nav--active');

    // Prevent FOUC, remove class hiding content
    this.element.classList.remove('js-hidden');

    this.stepNavSize = this.element.classList.contains('gem-c-step-nav--large') ? 'Big' : 'Small';
    this.rememberShownStep = !!this.element.hasAttribute('data-remember') && this.stepNavSize === 'Big';

    this.steps = this.element.querySelectorAll('.js-step');
    this.stepHeaders = this.element.querySelectorAll('.js-toggle-panel');
    this.totalSteps = this.element.querySelectorAll('.js-panel').length;
    this.totalLinks = this.element.querySelectorAll('.gem-c-step-nav__link').length;
    this.showOrHideAllButton = false;

    this.uniqueId = this.element.getAttribute('data-id') || false;

    if (this.uniqueId) {
      this.sessionStoreLink = `${this.sessionStoreLink}_${this.uniqueId}`;
    }

    this.upChevronSvg = '<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">' +
      '<path class="gem-c-step-nav__chevron-stroke" d="M19.5 10C19.5 15.2467 15.2467 19.5 10 19.5C4.75329 19.5 0.499997 15.2467 0.499998 10C0.499999 4.7533 4.7533 0.500001 10 0.500002C15.2467 0.500003 19.5 4.7533 19.5 10Z" stroke="#1D70B8"/>' +
      '<path class="gem-c-step-nav__chevron-stroke" d="M6.32617 12.3262L10 8.65234L13.6738 12.3262" stroke="#1D70B8" stroke-width="2"/>' +
      '</svg>';
    this.downChevronSvg = '<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">' +
      '<path class="gem-c-step-nav__chevron-stroke" d="M0.499997 10C0.499998 4.75329 4.75329 0.499999 10 0.499999C15.2467 0.5 19.5 4.75329 19.5 10C19.5 15.2467 15.2467 19.5 10 19.5C4.75329 19.5 0.499997 15.2467 0.499997 10Z" stroke="#1D70B8"/>' +
      '<path class="gem-c-step-nav__chevron-stroke" d="M13.6738 8.67383L10 12.3477L6.32617 8.67383" stroke="#1D70B8" stroke-width="2"/>' +
      '</svg>';

    var stepNavTracker = new StepNavTracker(this.uniqueId, this.totalSteps, this.totalLinks);

    this.getTextForInsertedElements();
    this.addButtonstoSteps();
    this.addShowHideAllButton();
    this.addShowHideToggle();
    this.addAriaControlsAttrForShowHideAllButton();

    this.ensureOnlyOneActiveLink();
    this.showPreviouslyOpenedSteps();

    this.bindToggleForSteps(stepNavTracker);
    this.bindToggleShowHideAllButton(stepNavTracker);
    this.bindComponentLinkClicks(stepNavTracker);
  }

  getTextForInsertedElements() {
    this.actions.showText = this.element.getAttribute('data-show-text');
    this.actions.hideText = this.element.getAttribute('data-hide-text');
    this.actions.showAllText = this.element.getAttribute('data-show-all-text');
    this.actions.hideAllText = this.element.getAttribute('data-hide-all-text');
  }

  addShowHideAllButton() {
    var showall = document.createElement('div');
    showall.className = 'gem-c-step-nav__controls govuk-!-display-none-print';
    showall.innerHTML = '<button aria-expanded="false" class="gem-c-step-nav__button gem-c-step-nav__button--controls js-step-controls-button">' +
      this.actions.showAllText +
      '</button>';

    var steps = this.element.querySelector('.gem-c-step-nav__steps');
    this.element.insertBefore(showall, steps);

    this.showOrHideAllButton = this.element.querySelector('.js-step-controls-button');
  }

  addShowHideToggle() {
    this.stepHeaders.forEach(thisel => {
      if (!thisel.querySelectorAll('.js-toggle-link').length) {
        var span = document.createElement('span');
        var showHideSpan = document.createElement('span');
        var showHideSpanText = document.createElement('span');
        var showHideSpanIcon = document.createElement('span');
        var commaSpan = document.createElement('span');
        var thisSectionSpan = document.createElement('span');

        showHideSpan.className = 'gem-c-step-nav__toggle-link js-toggle-link govuk-!-display-none-print';
        showHideSpanText.className = 'gem-c-step-nav__button-text js-toggle-link-text';
        showHideSpanIcon.className = 'gem-c-step-nav__chevron js-toggle-link-icon';
        commaSpan.className = 'govuk-visually-hidden';
        thisSectionSpan.className = 'govuk-visually-hidden';

        showHideSpan.appendChild(showHideSpanText);

        commaSpan.innerHTML = ', ';
        thisSectionSpan.innerHTML = ' this section';

        span.appendChild(commaSpan);
        span.appendChild(showHideSpan);
        span.appendChild(thisSectionSpan);

        thisel.querySelector('.js-step-title-button').appendChild(span);
      }
    });
  }

  headerIsOpen(stepHeader) {
    return (typeof stepHeader.parentNode.getAttribute('show') !== 'undefined');
  }

  addAriaControlsAttrForShowHideAllButton() {
    var ariaControlsValue = this.element.querySelector('.js-panel').getAttribute('id');
    this.showOrHideAllButton.setAttribute('aria-controls', ariaControlsValue);
  }

  // called by show all/hide all, sets all steps accordingly
  setAllStepsShownState(isShown) {
    var data = [];

    for (const step of this.steps) {
      var stepView = new StepView(step, this)
      stepView.setIsShown(isShown);

      if (isShown) {
        data.push(step.getAttribute('id'));
      }
    }

    if (isShown) {
      window.sessionStorage.setItem(this.uniqueId, JSON.stringify(data));
    } else {
      window.sessionStorage.removeItem(this.uniqueId);
    }
  }

  // called on load, determines whether each step should be open or closed
  showPreviouslyOpenedSteps() {
    var data = window.sessionStorage.getItem(this.uniqueId) || [];

    for (const thisel of this.steps) {
      var id = thisel.getAttribute('id');
      var stepView = new StepView(thisel, this);
      var shouldBeShown = thisel.hasAttribute('data-show');

      // show the step if it has been remembered or if it has the 'data-show' attribute
      if ((this.rememberShownStep && data.indexOf(id) > -1) || (shouldBeShown && shouldBeShown !== 'undefined')) {
        stepView.setIsShown(true);
      } else {
        stepView.setIsShown(false);
      }
    }

    if (data.length > 0) {
      this.showOrHideAllButton.setAttribute('aria-expanded', true);
      this.setShowHideAllText();
    }
  }

  addButtonstoSteps() {
    for (const thisel of this.steps) {
      var title = thisel.querySelector('.js-step-title');
      var contentId = thisel.querySelector('.js-panel').getAttribute('id');
      var titleText = title.textContent || title.innerText; // IE8 fallback

      title.outerHTML =
        '<span class="js-step-title">' +
          '<button ' +
            'class="gem-c-step-nav__button gem-c-step-nav__button--title js-step-title-button" ' +
            'aria-expanded="false" aria-controls="' + contentId + '">' +
              '<span class="gem-c-step-nav__title-text js-step-title-text">' + titleText + '</span>' +
          '</button>' +
        '</span>';
    }
  }

  bindToggleForSteps(stepNavTracker) {
    var togglePanels = this.element.querySelectorAll('.js-toggle-panel');

    for (const panel of togglePanels) {
      panel.addEventListener('click', (event) => {
        var stepView = new StepView(event.currentTarget.parentNode, this);
        stepView.toggle();

        var stepIsOptional = event.currentTarget.parentNode.hasAttribute('data-optional');
        var toggleClick = new StepToggleClick(event, stepView, stepNavTracker, stepIsOptional, this);
        toggleClick.trackClick();

        this.setShowHideAllText();
        this.rememberStepState(event.currentTarget.parentNode);
      });
    }
  }

  // if the step is open, store its id in session store
  // if the step is closed, remove its id from session store
  rememberStepState(step) {
    if (this.rememberShownStep) {
      var data = JSON.parse(window.sessionStorage.getItem(this.uniqueId)) || [];
      var thisstep = step.getAttribute('id');
      var shown = step.classList.contains('step-is-shown');

      if (shown) {
        data.push(thisstep);
      } else {
        var i = data.indexOf(thisstep);
        if (i > -1) {
          data.splice(i, 1);
        }
      }
      window.sessionStorage.setItem(this.uniqueId, JSON.stringify(data));
    }
  }

  // tracking click events on links in step content
  bindComponentLinkClicks(stepNavTracker) {
    var jsLinks = this.element.querySelectorAll('.js-link');

    for (const link of jsLinks) {
      link.addEventListener('click', event => {
        var dataPosition = event.target.getAttribute('data-position');
        var linkClick = new ComponentLinkClick(event, stepNavTracker, dataPosition, this.stepNavSize);
        linkClick.trackClick();

        if (event.target.getAttribute('rel') !== 'external') {
          window.sessionStorage.setItem(this.sessionStoreLink, dataPosition);
        }

        if (event.target.getAttribute('href') === this.activeLinkHref) {
          this.setOnlyThisLinkActive(event.target);
          this.setActiveStepClass();
        }
      });
    }
  }

  setOnlyThisLinkActive(clicked) {
    this.element.querySelectorAll('.' + this.activeLinkClass).forEach(link => {
      link.classList.remove(this.activeLinkClass);
    });
    clicked.parentNode.classList.add(this.activeLinkClass);
  }

  // if a link occurs more than once in a step nav, the backend doesn't know which one to highlight
  // so it gives all those links the 'active' attribute and highlights the last step containing that link
  // if the user clicked on one of those links previously, it will be in the session store
  // this code ensures only that link and its corresponding step have the highlighting
  // otherwise it accepts what the backend has already passed to the component
  ensureOnlyOneActiveLink() {
    var activeLinks = this.element.querySelectorAll('.js-list-item.' + this.activeLinkClass);

    if (activeLinks.length <= 1) {
      return;
    }

    var loaded = window.sessionStorage.getItem(this.sessionStoreLink);
    var activeParent = this.element.querySelector('.' + this.activeLinkClass);
    var activeChild = activeParent.firstChild;
    var foundLink = activeChild.getAttribute('data-position');
    var lastClicked = loaded || foundLink; // the value saved has priority

    // it's possible for the saved link position value to not match any of the currently duplicate highlighted links
    // so check this otherwise it'll take the highlighting off all of them
    var checkLink = this.element.querySelector('[data-position="' + lastClicked + '"]');

    if (checkLink) {
      if (!checkLink.parentNode.classList.contains(this.activeLinkClass)) {
        lastClicked = checkLink;
      }
    } else {
      lastClicked = foundLink;
    }

    this.removeActiveStateFromAllButCurrent(activeLinks, lastClicked);
    this.setActiveStepClass();
  }

  removeActiveStateFromAllButCurrent(activeLinks, current) {
    for (const thisel of activeLinks) {
      if (thisel.querySelector('.js-link').getAttribute('data-position').toString() !== current.toString()) {
        thisel.classList.remove(this.activeLinkClass);
        var visuallyHidden = thisel.querySelectorAll('.visuallyhidden');
        if (visuallyHidden.length) {
          visuallyHidden[0].parentNode.removeChild(visuallyHidden[0]);
        }
      }
    }
  }

  setActiveStepClass() {
    // remove the 'active/open' state from all steps
    var allActiveSteps = this.element.querySelectorAll('.' + this.activeStepClass);
    for (const step of allActiveSteps) {
      step.classList.remove(this.activeStepClass);
      step.removeAttribute('data-show');
    }

    // find the current page link and apply 'active/open' state to parent step
    var activeLink = this.element.querySelector('.' + this.activeLinkClass);
    if (activeLink) {
      var activeStep = activeLink.closest('.gem-c-step-nav__step');
      activeStep.classList.add(this.activeStepClass);
      activeStep.setAttribute('data-show', '');
    }
  }

  bindToggleShowHideAllButton(stepNavTracker) {
    this.showOrHideAllButton.addEventListener('click', event => {
      var textContent = event.target.textContent || event.target.innerText;
      var shouldShowAll = textContent === this.actions.showAllText;

      // Fire GA click tracking
      stepNavTracker.trackClick('pageElementInteraction', (shouldShowAll ? 'stepNavAllShown' : 'stepNavAllHidden'), {
        label: (shouldShowAll ? this.actions.showAllText : this.actions.hideAllText) + ': ' + this.stepNavSize
      })

      this.setAllStepsShownState(shouldShowAll);
      this.showOrHideAllButton.setAttribute('aria-expanded', shouldShowAll);
      this.setShowHideAllText();

      return false;
    });
  }

  setShowHideAllText() {
    var shownSteps = this.element.querySelectorAll('.step-is-shown').length;

    // Find out if the number of is-opens == total number of steps
    var shownStepsIsTotalSteps = shownSteps === this.totalSteps;

    this.showOrHideAllButton.innerHTML = shownStepsIsTotalSteps ? this.actions.hideAllText : this.actions.showAllText;
  }
}

class StepView {

  constructor(stepElement, stepNav) {
    this.stepElement = stepElement;
    this.stepContent = this.stepElement.querySelector('.js-panel');
    this.titleButton = this.stepElement.querySelector('.js-step-title-button');
    var textElement = this.stepElement.querySelector('.js-step-title-text');
    this.title = textElement.textContent || textElement.innerText;
    this.title = this.title.replace(/^\s+|\s+$/g, ''); // this is 'trim' but supporting IE8
    this.showText = stepNav.actions.showText;
    this.hideText = stepNav.actions.hideText;
    this.upChevronSvg = stepNav.upChevronSvg;
    this.downChevronSvg = stepNav.downChevronSvg;
  }

  show() {
    this.setIsShown(true);
  }

  hide() {
    this.setIsShown(false);
  }

  toggle() {
    this.setIsShown(this.isHidden());
  }

  setIsShown(isShown) {
    if (isShown) {
      this.stepElement.classList.add('step-is-shown');
      this.stepContent.classList.remove('js-hidden');
    } else {
      this.stepElement.classList.remove('step-is-shown');
      this.stepContent.classList.add('js-hidden');
    }

    this.titleButton.setAttribute('aria-expanded', isShown);
    var showHideText = this.stepElement.querySelector('.js-toggle-link');

    showHideText.querySelector('.js-toggle-link-text').innerHTML = isShown ? this.hideText : this.showText;
  }

  isShown() {
    return this.stepElement.classList.contains('step-is-shown');
  }

  isHidden() {
    return !this.isShown();
  }

  numberOfContentItems() {
    return this.stepContent.querySelectorAll('.js-link').length;
  }
}

class StepToggleClick {

  constructor(event, stepView, stepNavTracker, stepIsOptional, stepNav) {
    this.target = event.target;
    this.stepIsOptional = stepIsOptional;
    this.stepNav = stepNav;
    this.stepNavSize = this.stepNav.stepNavSize;
    this.stepNavTracker = stepNavTracker;
    this.stepView = stepView;
  }

  trackClick() {
    var trackingOptions = {
      label: this.trackingLabel(),
      dimension28: this.stepView.numberOfContentItems().toString()
    };
    this.stepNavTracker.trackClick('pageElementInteraction', this.trackingAction(), trackingOptions);
  }

  trackingLabel() {
    var clickedNearbyToggle = this.target.closest('.js-step').querySelector('.js-toggle-panel');
    return clickedNearbyToggle.getAttribute('data-position') + ' - ' + this.stepView.title + ' - ' + this.locateClickElement() + ': ' + this.stepNavSize + this.isOptional();
  }

  // returns index of the clicked step in the overall number of steps
  stepIndex() { // eslint-disable-line no-unused-vars
    return this.stepNav.steps.index(this.stepView.element) + 1;
  }

  trackingAction() {
    return (this.stepView.isHidden() ? 'stepNavHidden' : 'stepNavShown');
  }

  locateClickElement() {
    if (this.clickedOnIcon()) {
      return this.iconType() + ' click';
    } else if (this.clickedOnHeading()) {
      return 'Heading click';
    } else {
      return 'Elsewhere click';
    }
  }

  clickedOnIcon() {
    return this.target.classList.contains('js-toggle-link');
  }

  clickedOnHeading() {
    return this.target.classList.contains('js-step-title-text');
  }

  iconType() {
    return (this.stepView.isHidden() ? 'Minus' : 'Plus');
  }

  isOptional() {
    return (this.stepIsOptional ? ' ; optional' : '');
  }
}

class ComponentLinkClick {

  constructor(event, stepNavTracker, linkPosition, size) {
    this.size = size;
    this.target = event.target;
    this.stepNavTracker = stepNavTracker;
    this.linkPosition = linkPosition;
  }

  trackClick() {
    var trackingOptions = { label: this.target.getAttribute('href') + ' : ' + this.size };
    var dimension28 = this.target.closest('.gem-c-step-nav__list').getAttribute('data-length');

    if (dimension28) {
      trackingOptions.dimension28 = dimension28;
    }

    this.stepNavTracker.trackClick('stepNavLinkClicked', this.linkPosition, trackingOptions);
  }
}

// A helper that sends a custom event request to Google Analytics if
// the GOVUK module is setup
class StepNavTracker {
  constructor(uniqueId, totalSteps, totalLinks) {
    this.totalSteps = totalSteps;
    this.totalLinks = totalLinks;
    this.uniqueId = uniqueId;
  }

  trackClick(category, action, options) {
    // dimension26 records the total number of expand/collapse steps in this step nav
    // dimension27 records the total number of links in this step nav
    // dimension28 records the number of links in the step that was shown/hidden (handled in click event)
    if (window.GOVUK && window.GOVUK.analytics && window.GOVUK.analytics.trackEvent) {
      options = options || {};
      options.dimension26 = options.dimension26 || this.totalSteps.toString();
      options.dimension27 = options.dimension27 || this.totalLinks.toString();
      options.dimension96 = options.dimension96 || this.uniqueId;
      window.GOVUK.analytics.trackEvent(category, action, options);
    }
  }
}

function initStepNav() {
  document.querySelectorAll('[data-module="gemstepnav"]').forEach(el => { new StepNav(el); });
}

export default initStepNav;
