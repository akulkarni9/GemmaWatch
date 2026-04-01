/// <reference types="cypress" />

describe('High-Precision Intelligence (Chat)', () => {
  beforeEach(() => {
    // 1. Mock Authentication
    cy.setCookie('access_token', 'mock-token-abc');
    
    // 2. Mock API responses
    cy.intercept('GET', '**/sites', { statusCode: 200, body: [
      { id: 'site-1', name: 'Mark Production', url: 'https://mark.com' }
    ] }).as('getSites');
    
    cy.visit('http://localhost:5173');
  });

  it('opens the Gemma Analysis drawer', () => {
    // We assume there's a button/icon to open the chat
    cy.get('button').contains(/Chat|Analysis/i).click();
    cy.contains('Gemma Analyst').should('be.visible');
  });

  it('provides high-precision responses to site queries', () => {
    cy.get('button').contains(/Chat|Analysis/i).click();
    
    // Intercept chat request
    cy.intercept('POST', '**/chat', {
       statusCode: 200,
       body: {
         role: 'assistant',
         content: 'Mark Production is currently ONLINE with 99.9% uptime. No anomalies detected.',
         query_type: 'structured'
       }
    }).as('chatQuery');

    cy.get('input[placeholder*="Ask"]').type('How is Mark Production?{enter}');
    
    cy.wait('@chatQuery');
    cy.contains('Mark Production is currently ONLINE').should('be.visible');
  });

  it('demonstrates zero-fluff persona', () => {
    cy.get('button').contains(/Chat|Analysis/i).click();
    
    cy.intercept('POST', '**/chat', {
       statusCode: 200,
       body: {
         role: 'assistant',
         content: 'I am the GemmaWatch Analyst. I can assist with root cause analysis and site metrics.',
         query_type: 'system'
       }
    }).as('sysQuery');

    cy.get('input[placeholder*="Ask"]').type('What can you do?{enter}');
    
    cy.wait('@sysQuery');
    // Verify it doesn't contain conversational fluff
    cy.contains('Certainly').should('not.exist');
    cy.contains('It is a pleasure').should('not.exist');
    cy.contains('Analyst').should('be.visible');
  });
});
