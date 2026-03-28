/// <reference types="cypress" />

describe('Monitoring & Real-time Dashboard', () => {
  beforeEach(() => {
    cy.intercept('GET', '**/sites', { statusCode: 200, body: [] }).as('getSites');
    cy.visit('http://localhost:5173');
  });

  it('loads dashboard', () => {
    cy.contains('GemmaWatch AI').should('be.visible');
  });

  it('displays Live Activity section', () => {
    cy.contains('Live Activity').should('be.visible');
  });

  it('shows Add Site button', () => {
    cy.contains('Add Site').should('be.visible');
  });

  it('displays filters and search', () => {
    cy.get('select').should('exist');
    cy.get('input').should('have.length.greaterThan', 0);
  });

  it('remains responsive on mobile', () => {
    cy.viewport(375, 812);
    cy.contains('GemmaWatch AI').should('be.visible');
  });

  it('remains responsive on tablet', () => {
    cy.viewport(768, 1024);
    cy.contains('GemmaWatch AI').should('be.visible');
  });

  it('displays metrics on desktop', () => {
    cy.viewport(1280, 720);
    cy.contains('Total Checks').should('exist');
    cy.contains('Pass Rate').should('exist');
  });
});
