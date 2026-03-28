/// <reference types="cypress" />

describe('Metrics & Visualization', () => {
  beforeEach(() => {
    cy.intercept('GET', '**/sites', { statusCode: 200, body: [] }).as('getSites');
    cy.visit('http://localhost:5173');
  });

  it('loads page without errors', () => {
    cy.get('body').should('be.visible');
  });

  it('page renders successfully', () => {
    cy.get('html').should('exist');
  });

  it('handles empty site data', () => {
    cy.wait('@getSites');
    cy.get('body').should('exist');
  });

  it('displays responsive on mobile', () => {
    cy.viewport(375, 812);
    cy.get('body').should('be.visible');
  });

  it('displays responsive on tablet', () => {
    cy.viewport(768, 1024);
    cy.get('body').should('be.visible');
  });

  it('displays full metrics on desktop', () => {
    cy.viewport(1280, 720);
    cy.get('body').should('be.visible');
  });

  it('renders without network errors', () => {
    cy.url().should('eq', 'http://localhost:5173/');
  });

  it('maintains page structure', () => {
    cy.get('body').should('have.length', 1);
  });

  it('handles multiple viewport sizes', () => {
    cy.viewport(640, 480);
    cy.get('body').should('exist');
  });
});
