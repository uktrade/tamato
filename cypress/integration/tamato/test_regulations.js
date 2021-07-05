
/*

Questions
--
* What approaches are there to rebuilding test database - TaMaTo DB is big.
* How is context data around failures preserved?
* How do we persist DOM snapshots?
* Where are DOM snapshots stored?
* Best practices for pipeline integration.

Notes
--
* Cypress best practice suggests using a 'data-cy' attribute to target
  DOM elements. For Fire Break expediency we've mostly kept our templates
  unchanged, but would consider this approach if choosing to adopt Cypress.
* Visual testing possible using cy.screenshot().
* Could do screenshot comparisons against a baseline snapshot.
* Start GUI:
   $ npm run cypress:open 
* Using a scripts entry:
    "cypress:headless": \
        "CYPRESS_integrationFolder=cypress/integration/tamato \
        cypress run --headless --browser chrome"
  From npm CLI:
    $ npm run cypress:headless
* Cypress site publishes some best practices,
  https://docs.cypress.io/guides/references/best-practices:
  - Application login.
  - Selecting Elements. 
  - Assigning return values.
  - Visiting external sites.
  - Coupling tests.
**/


describe('Regulations', () => {
    context('Filter', () => {
        it('Regulation by ID', () => {
            // FR-001 - Verify home page can be displayed.
            // --
            cy.visit('http://localhost:8000/')
            cy.title()
                .should('include', 'Manage trade tariffs | Manage Trade Tariffs')

            // FR-002 - Verify can click link that navigates to
            // "Find and edit regulations" page.
            // --
            // An example of Cypress's best practice of using a "data-""
            // attribute. Here using data-tt (tt="test target", rather than the
            // data-cy suggested by Cypress):
            cy.get('[data-tt="find-and-edit-regulation"]')
                .click()
            // Anti-pattern would be to use, say, text content that could change:
            //cy.get('a').contains('Find and edit regulations').click()

            // FR-003 - Verify “Find and edit regulations” page is displayed.
            // --
            cy.get('h1')
                .should('contain', 'Find and edit regulations')

            // FR-004 - Verify user can enter search text.
            // --
            cy.get('input#id_search')
                .type('R9600060')

            // FR-005 - Verify user can submit search text.
            // --
            cy.get('#id_submit')
                .click()

            // FR-006 - Verify search results contains regulation.
            // FR-007 - Verify user can click regulation R9600060.
            // --
            cy.get('a')
                .contains('R9600060')
                .click()

            // FR-008 - Verify regulation details page displays regulation
            // ID “R9600060”.
            // --
            cy.url()
                .should('include', 'R9600060')

            // We can even take screenshots.
            cy.screenshot()
        })
    })

    context('Create', () => {
        it('Regulation', () => {
            // FR-001 - Verify home page can be displayed.
            // --
            cy.visit('http://localhost:8000/')
            cy.title()
                .should('include', 'Manage trade tariffs | Manage Trade Tariffs')

            // FR-002 - Verify can click link that navigates to
            // “Create regulations” page.
            // --
            // An example of Cypress's best practice of using a "data-""
            // attribute. Here using data-tt (tt="test target", rather than the
            // data-cy suggested by Cypress):
            cy.get('[data-tt="create-regulations"]')
                .click()

        })
    })
})
