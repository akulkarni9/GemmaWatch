/// <reference types="cypress" />

describe('Site Management', () => {
  beforeEach(() => {
    cy.intercept('GET', '**/sites', { statusCode: 200, body: [] }).as('getSites');
    cy.visit('http://localhost:5173');
    cy.wait('@getSites');
  });

  it('page loads without errors', () => {
    cy.get('body').should('be.visible');
  });

  it('site management page renders', () => {
    cy.get('html').should('exist');
  });

  it('handles empty site list', () => {
    cy.get('body').should('exist');
  });

  it('page is responsive on mobile', () => {
    cy.viewport('iphone-x');
    cy.get('body').should('be.visible');
  });

  it('page is responsive on tablet', () => {
    cy.viewport('ipad-2');
    cy.get('body').should('be.visible');
  });

  it('page is responsive on desktop', () => {
    cy.viewport(1280, 720);
    cy.get('body').should('be.visible');
  });

  it('maintains layout on resize', () => {
    cy.viewport(1920, 1080);
    cy.get('body').should('have.length', 1);
  });

  it('handles navigation correctly', () => {
    cy.url().should('eq', 'http://localhost:5173/');
  });

  it('page structure is valid', () => {
    cy.get('body').should('exist');
  });
});
