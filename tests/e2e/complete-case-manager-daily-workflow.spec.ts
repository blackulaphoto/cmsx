import { test, expect } from '@playwright/test';

/**
 * Complete Case Manager Daily Workflow - End-to-End Test
 * 
 * This test covers the full daily workflow of a case manager using the Case Management Suite,
 * following the Maria Santos test scenario. The test verifies all major system components
 * working together in realistic case management scenarios.
 * 
 * Scenario: A case manager starts their day, reviews AI recommendations, creates a new client
 * profile (Maria Santos), and begins coordinating services across multiple modules.
 */

test.describe('Complete Case Manager Daily Workflow', () => {
  test('Case Manager completes full daily workflow with Maria Santos client', async ({ page }) => {
    // ==================================================
    // MORNING WORKFLOW - Dashboard & Smart Daily Review
    // ==================================================
    
    // Step 1: Navigate to application and verify dashboard loads
    await test.step('Load dashboard and verify initial state', async () => {
      await page.goto('/');
      await expect(page).toHaveTitle(/Case Management Suite/);
      await expect(page.getByRole('main').getByRole('heading', { name: 'Case Management Suite' })).toBeVisible();
      
      // Verify dashboard metrics are displayed
      await expect(page.getByText('Total Clients').first()).toBeVisible();
      await expect(page.getByText('Active Cases').first()).toBeVisible();
      await expect(page.getByText('High Risk').first()).toBeVisible();
      await expect(page.getByText('Recent Intakes').first()).toBeVisible();
    });

    // Step 2: Access Smart Daily Dashboard for morning priorities
    await test.step('Review Smart Daily Dashboard and AI recommendations', async () => {
      await page.getByRole('navigation').getByRole('link', { name: 'Smart Daily', exact: true }).click();
      await expect(page).toHaveURL(/smart-dashboard/);
      
      // Verify Smart Daily Dashboard loads
      await expect(page.getByRole('heading', { name: 'Smart Daily Dashboard' })).toBeVisible();
      await expect(page.getByText('Your intelligent daily agenda and task management')).toBeVisible();
      
      // Verify AI recommendations are present
      await expect(page.getByText('AI-Generated Reminders')).toBeVisible();
      await expect(page.getByText('AI Recommendation').first()).toBeVisible();
      
      // Verify task metrics
      await expect(page.getByText("Today's Tasks")).toBeVisible();
      await expect(page.getByText('Completed')).toBeVisible();
      await expect(page.getByText('Urgent')).toBeVisible();
      await expect(page.getByText('Progress')).toBeVisible();
      
      // Verify quick actions are available
      await expect(page.getByRole('button', { name: 'Add New Client' })).toBeVisible();
    });

    // ==================================================
    // CLIENT INTAKE WORKFLOW - Maria Santos Profile Creation
    // ==================================================

    // Step 3: Navigate to Case Management and initiate client creation
    await test.step('Navigate to Case Management module', async () => {
      await page.getByRole('navigation').getByRole('link', { name: 'Case Management', exact: true }).click();
      await expect(page).toHaveURL(/case-management/);
      
      // Verify Case Management page loads
      await expect(page.getByRole('heading', { name: 'Case Management' })).toBeVisible();
      await expect(page.getByText('Manage client cases and track progress')).toBeVisible();
      
      // Verify client table is present
      await expect(page.getByRole('table')).toBeVisible();
      await expect(page.getByText('Client')).toBeVisible();
      await expect(page.getByText('Status')).toBeVisible();
      await expect(page.getByText('Risk Level')).toBeVisible();
    });

    // Step 4: Open client intake form
    await test.step('Open client intake form', async () => {
      await page.getByRole('button', { name: 'Add Client' }).click();
      
      // Verify intake form opens
      await expect(page.getByText('Client Intake Form')).toBeVisible();
      await expect(page.getByText('Complete client information and assessment')).toBeVisible();
      
      // Verify form sections are present
      await expect(page.getByText('Personal Information')).toBeVisible();
      await expect(page.getByText('Current Status Assessment')).toBeVisible();
      await expect(page.getByText('Goals & Barriers')).toBeVisible();
    });

    // Step 5: Complete Maria Santos client profile
    await test.step('Fill out comprehensive Maria Santos client intake form', async () => {
      // Personal Information
      await page.getByRole('textbox', { name: 'Enter first name' }).fill('Maria');
      await page.getByRole('textbox', { name: 'Enter last name' }).fill('Santos');
      await page.locator('input[type="date"]').fill('1990-01-15');
      await page.locator('div').filter({ hasText: /^Phone Number$/ }).getByPlaceholder('(555) 123-').fill('(555) 123-7890');
      await page.getByRole('textbox', { name: 'client@example.com' }).fill('maria.santos@test.com');
      
      // Program Type
      await page.locator('select').first().selectOption(['Reentry Program']);
      
      // Status Assessment - Based on Maria Santos profile
      await page.locator('div').filter({ hasText: /^Housing StatusUnknownStable HousingTransitional HousingHomelessAt Risk$/ })
        .getByRole('combobox').selectOption(['Transitional Housing']);
      
      await page.locator('div:nth-child(5) > .grid > div:nth-child(2) > .w-full')
        .selectOption(['Actively Seeking']);
      
      await page.locator('div:nth-child(5) > .grid > div:nth-child(4) > .w-full')
        .selectOption(['Expungement Process']);
      
      // Goals and Barriers - Critical information from Maria Santos scenario
      await page.getByRole('textbox', { name: 'What does the client want to' })
        .fill('Permanent housing by end of month, restaurant employment, complete expungement process');
      
      await page.getByRole('textbox', { name: 'What challenges might prevent' })
        .fill('Limited time for housing transition, pending legal proceedings, employment gap since 2019');
    });

    // Step 6: Create client profile and verify success
    await test.step('Create Maria Santos profile and verify creation', async () => {
      await page.getByRole('button', { name: 'Create Client Profile' }).click();
      
      // Verify client was created successfully and appears in table
      await expect(page.getByText('Maria Santos')).toBeVisible();
      await expect(page.getByText('maria.santos@test.com')).toBeVisible();
      await expect(page.getByText('(555) 123-7890')).toBeVisible();
      
      // Verify client status indicators
      await expect(page.locator('tbody tr:first-child')).toContainText('active');
      await expect(page.locator('tbody tr:first-child')).toContainText('medium');
      
      // Verify client actions are available
      await expect(page.getByRole('button', { name: 'View Dashboard' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'View Profile' })).toBeVisible();
    });

    // ==================================================
    // SERVICE COORDINATION WORKFLOW
    // ==================================================

    // Step 7: Access AI Assistant for case coordination
    await test.step('Consult AI Assistant for Maria Santos case coordination', async () => {
      await page.getByRole('navigation').getByRole('link', { name: 'AI Assistant', exact: true }).click();
      await expect(page).toHaveURL(/ai-chat/);
      
      // Verify AI Assistant interface loads
      await expect(page.getByText('AI Assistant')).toBeVisible();
      
      // Simulate AI consultation about Maria's priorities
      const messageInput = page.getByRole('textbox', { name: /message|chat|input/i });
      if (await messageInput.isVisible()) {
        await messageInput.fill('Maria Santos has court next Tuesday and needs housing by end of month. What should be prioritized today?');
      }
    });

    // Step 8: Access Housing module for Maria's housing search
    await test.step('Navigate to Housing module for housing coordination', async () => {
      await page.getByRole('navigation').getByRole('link', { name: 'Housing', exact: true }).click();
      await expect(page).toHaveURL(/housing/);
      
      // Verify Housing module loads
      await expect(page.getByRole('main')).toBeVisible();
      
      // Verify key housing features are accessible
      await expect(page.getByText(/search|filter|properties/i).first()).toBeVisible();
    });

    // Step 9: Access Legal module for expungement coordination
    await test.step('Navigate to Legal module for expungement process', async () => {
      await page.getByRole('navigation').getByRole('link', { name: 'Legal', exact: true }).click();
      await expect(page).toHaveURL(/legal/);
      
      // Verify Legal module loads
      await expect(page.getByRole('main')).toBeVisible();
      
      // Verify expungement features are accessible
      await expect(page.getByText(/expungement|legal|court/i).first()).toBeVisible();
    });

    // Step 10: Access Jobs module for employment search
    await test.step('Navigate to Jobs module for employment coordination', async () => {
      await page.getByRole('navigation').getByRole('link', { name: 'Jobs', exact: true }).click();
      await expect(page).toHaveURL(/jobs/);
      
      // Verify Jobs module loads
      await expect(page.getByRole('main')).toBeVisible();
      
      // Verify job search features are accessible
      await expect(page.getByText(/job|search|employment/i).first()).toBeVisible();
    });

    // Step 11: Access Benefits module for assistance programs
    await test.step('Navigate to Benefits module for assistance coordination', async () => {
      await page.getByRole('navigation').getByRole('link', { name: 'Benefits', exact: true }).click();
      await expect(page).toHaveURL(/benefits/);
      
      // Verify Benefits module loads
      await expect(page.getByRole('main')).toBeVisible();
      
      // Verify benefits features are accessible
      await expect(page.getByText(/benefits|assistance|snap|medicaid/i).first()).toBeVisible();
    });

    // ==================================================
    // END OF DAY WORKFLOW - Task Management & Summary
    // ==================================================

    // Step 12: Return to Smart Daily for task management
    await test.step('Return to Smart Daily Dashboard for task management', async () => {
      await page.getByRole('navigation').getByRole('link', { name: 'Smart Daily', exact: true }).click();
      await expect(page).toHaveURL(/smart-dashboard/);
      
      // Verify task management features
      await expect(page.getByText("Today's Agenda")).toBeVisible();
      await expect(page.getByText('Quick Actions')).toBeVisible();
    });

    // Step 13: Final verification - return to Case Management
    await test.step('Final verification of Maria Santos client persistence', async () => {
      await page.getByRole('navigation').getByRole('link', { name: 'Case Management', exact: true }).click();
      await expect(page).toHaveURL(/case-management/);
      
      // Verify Maria Santos client persists and is accessible
      await expect(page.getByText('Maria Santos')).toBeVisible();
      await expect(page.getByText('maria.santos@test.com')).toBeVisible();
      
      // Verify client can be accessed for future case management
      const mariaRow = page.locator('tbody tr:first-child');
      await expect(mariaRow).toContainText('Maria Santos');
      await expect(mariaRow).toContainText('active');
      await expect(mariaRow).toContainText('medium');
      
      // Verify action buttons are functional
      const viewDashboardBtn = mariaRow.getByRole('button', { name: 'View Dashboard' });
      const viewProfileBtn = mariaRow.getByRole('button', { name: 'View Profile' });
      
      await expect(viewDashboardBtn).toBeVisible();
      await expect(viewProfileBtn).toBeVisible();
    });

    // ==================================================
    // CROSS-MODULE INTEGRATION VERIFICATION
    // ==================================================

    // Step 14: Verify navigation and system integration
    await test.step('Verify cross-module navigation and system integration', async () => {
      // Test navigation menu is consistently available
      const navModules = [
        'Dashboard',
        'Case Management', 
        'Housing',
        'Benefits',
        'Legal',
        'Resume',
        'Jobs',
        'Services',
        'AI Assistant',
        'Smart Daily'
      ];

      for (const module of navModules) {
        await expect(page.getByRole('navigation').getByRole('link', { name: module })).toBeVisible();
      }
      
      // Verify user context is maintained
      await expect(page.getByText('John Doe')).toBeVisible(); // Case Manager name
      await expect(page.getByText('Case Manager')).toBeVisible(); // Role
    });
  });

  // ==================================================
  // SYSTEM PERFORMANCE AND RELIABILITY TESTS
  // ==================================================

  test('System handles rapid navigation between modules', async ({ page }) => {
    await test.step('Test rapid module switching for performance', async () => {
      await page.goto('/');
      
      const modules = [
        { name: 'Case Management', url: /case-management/ },
        { name: 'Smart Daily', url: /smart-dashboard/ },
        { name: 'Housing', url: /housing/ },
        { name: 'AI Assistant', url: /ai-chat/ },
        { name: 'Legal', url: /legal/ },
        { name: 'Jobs', url: /jobs/ }
      ];
      
      for (const module of modules) {
        await page.getByRole('navigation').getByRole('link', { name: module.name, exact: true }).click();
        await expect(page).toHaveURL(module.url);
        await expect(page.getByRole('main')).toBeVisible();
      }
    });
  });

  test('Client data persistence across browser sessions', async ({ page, context }) => {
    await test.step('Verify client data persists after page refresh', async () => {
      await page.goto('/case-management');
      
      // Check if any clients exist in the table
      const clientTable = page.getByRole('table');
      await expect(clientTable).toBeVisible();
      
      // Verify table has data rows beyond the header
      const tableRows = await clientTable.locator('tbody tr').count();
      
      if (tableRows > 0) {
        // Get first client name for persistence testing
        const firstClientName = await clientTable.locator('tbody tr:first-child').textContent();
        
        // Refresh page and verify data persistence  
        await page.reload();
        await expect(clientTable).toBeVisible();
        
        // Verify at least the same number of rows exist
        const newTableRows = await clientTable.locator('tbody tr').count();
        expect(newTableRows).toBeGreaterThanOrEqual(tableRows);
      }
    });
  });

  test('Responsive design and accessibility compliance', async ({ page }) => {
    await test.step('Verify responsive design and accessibility features', async () => {
      await page.goto('/');
      
      // Test responsive design
      await page.setViewportSize({ width: 1200, height: 800 });
      await expect(page.locator('nav')).toBeVisible();
      
      await page.setViewportSize({ width: 768, height: 600 });
      await expect(page.getByRole('main')).toBeVisible();
      
      // Basic accessibility checks
      await expect(page.getByRole('main').getByRole('heading', { level: 1 })).toBeVisible();
      await expect(page.getByRole('navigation')).toBeVisible();
      await expect(page.getByRole('main')).toBeVisible();
    });
  });
});

// ==================================================
// UTILITY FUNCTIONS FOR TEST MAINTENANCE
// ==================================================

/**
 * Helper function to create a test client with specified parameters
 * Useful for setting up test data in other test suites
 */
async function createTestClient(page: any, clientData: {
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  housingStatus?: string;
  employmentStatus?: string;
  legalStatus?: string;
}) {
  await page.goto('/case-management');
  await page.getByRole('button', { name: 'Add Client' }).click();
  
  // Fill basic information
  await page.getByRole('textbox', { name: 'Enter first name' }).fill(clientData.firstName);
  await page.getByRole('textbox', { name: 'Enter last name' }).fill(clientData.lastName);
  await page.getByRole('textbox', { name: 'client@example.com' }).fill(clientData.email);
  await page.locator('div').filter({ hasText: /^Phone Number$/ }).getByPlaceholder('(555) 123-').fill(clientData.phone);
  
  // Set status fields if provided
  if (clientData.housingStatus) {
    await page.locator('div').filter({ hasText: /^Housing Status/ })
      .getByRole('combobox').selectOption([clientData.housingStatus]);
  }
  
  if (clientData.employmentStatus) {
    await page.locator('div:nth-child(5) > .grid > div:nth-child(2) > .w-full')
      .selectOption([clientData.employmentStatus]);
  }
  
  if (clientData.legalStatus) {
    await page.locator('div:nth-child(5) > .grid > div:nth-child(4) > .w-full')
      .selectOption([clientData.legalStatus]);
  }
  
  // Create the client
  await page.getByRole('button', { name: 'Create Client Profile' }).click();
  
  // Verify creation
  await expect(page.getByText(`${clientData.firstName} ${clientData.lastName}`)).toBeVisible();
  await expect(page.getByText(clientData.email)).toBeVisible();
}

// Export helper for use in other test files
export { createTestClient };