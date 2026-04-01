/// <reference types="cypress" />

describe('Intelligent Catalogue HITL Approval', () => {
  beforeEach(() => {
    // 1. Login as Admin
    cy.setCookie('access_token', 'mock-admin-token');
    
    // 2. Mock Pending Catalogue Data
    cy.intercept('GET', '**/catalogue/pending', {
      statusCode: 200,
      body: [
        {
          id: 'p-1',
          category: 'Frontend',
          confidence: 0.88,
          rca_json: JSON.stringify({
            probable_cause: 'CSS Regression on Button',
            repair_action: 'Revert styling change'
          }),
          created_at: new Date().toISOString()
        }
      ]
    }).as('getPending');

    cy.visit('http://localhost:5173');
    // Navigate to Catalogue (Assuming it's a tab or link)
    cy.contains(/Catalogue|Intelligence/i).click();
  });

  it('displays pending entries for review', () => {
    cy.contains('Pending').click();
    cy.contains('CSS Regression on Button').should('be.visible');
    cy.contains('88%').should('be.visible');
  });

  it('allows approving an RCA entry', () => {
    cy.contains('Pending').click();
    
    // Intercept approval request
    cy.intercept('POST', '**/catalogue/approve/p-1', {
      statusCode: 200,
      body: { catalogue_id: 'c-1', embedded: true }
    }).as('approveEntry');

    // Click Approve button
    cy.get('button').contains(/Approve/i).click();
    
    cy.wait('@approveEntry');
    cy.contains('Approved Successfully').should('be.visible');
    cy.contains('CSS Regression on Button').should('not.exist'); // Entry should clear from pending
  });

  it('allows rejecting a low quality entry', () => {
    cy.contains('Pending').click();
    
    cy.intercept('POST', '**/catalogue/reject/p-1', {
      statusCode: 200,
      body: { status: 'rejected' }
    }).as('rejectEntry');

    cy.get('button').contains(/Reject/i).click();
    cy.wait('@rejectEntry');
    cy.contains('CSS Regression on Button').should('not.exist');
  });
});
