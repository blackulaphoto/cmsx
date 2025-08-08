import { test, expect } from '@playwright/test';

/**
 * Basic Case Manager Daily Workflow - End-to-End Test
 * 
 * This test covers the essential daily workflow of a case manager using the Case Management Suite.
 * It focuses on core functionality without complex selector conflicts.
 */

test.describe('Basic Case Manager Daily Workflow', () => {
  test('Case manager navigates through system and creates Maria Santos client', async ({ page }) => {
    // Step 1: Load application
    await page.goto('/');
    await expect(page).toHaveTitle(/Case Management Suite/);
    
    // Step 2: Navigate to Smart Daily Dashboard
    await page.getByRole('navigation').getByRole('link', { name: 'Smart Daily', exact: true }).click();
    await expect(page).toHaveURL(/smart-dashboard/);
    await expect(page.getByRole('main')).toBeVisible();
    
    // Step 3: Navigate to Case Management
    await page.getByRole('navigation').getByRole('link', { name: 'Case Management', exact: true }).click();
    await expect(page).toHaveURL(/case-management/);
    await expect(page.getByRole('table')).toBeVisible();
    
    // Step 4: Create new client
    await page.getByRole('button', { name: 'Add Client' }).click();
    await expect(page.getByText('Client Intake Form')).toBeVisible();
    
    // Step 5: Fill out test client profile (with unique name to avoid conflicts)
    const timestamp = Date.now();
    await page.getByRole('textbox', { name: 'Enter first name' }).fill('Test');
    await page.getByRole('textbox', { name: 'Enter last name' }).fill(`Client${timestamp}`);
    await page.locator('input[type="date"]').fill('1990-01-15');
    await page.locator('div').filter({ hasText: /^Phone Number$/ }).getByPlaceholder('(555) 123-').fill('(555) 123-7890');
    await page.getByRole('textbox', { name: 'client@example.com' }).fill(`test.client${timestamp}@test.com`);
    
    // Fill key status fields
    await page.locator('div').filter({ hasText: /^Housing StatusUnknownStable HousingTransitional HousingHomelessAt Risk$/ })
      .getByRole('combobox').selectOption(['Transitional Housing']);
    
    await page.locator('div:nth-child(5) > .grid > div:nth-child(2) > .w-full')
      .selectOption(['Actively Seeking']);
    
    await page.locator('div:nth-child(5) > .grid > div:nth-child(4) > .w-full')
      .selectOption(['Expungement Process']);
    
    // Fill goals and barriers
    await page.getByRole('textbox', { name: 'What does the client want to' })
      .fill('Permanent housing by end of month, restaurant employment, complete expungement process');
    
    await page.getByRole('textbox', { name: 'What challenges might prevent' })
      .fill('Limited time for housing transition, pending legal proceedings, employment gap since 2019');
    
    // Step 6: Create client profile
    await page.getByRole('button', { name: 'Create Client Profile' }).click();
    
    // Step 7: Verify client was created
    await expect(page.getByText(`Test Client${timestamp}`)).toBeVisible();
    await expect(page.getByText(`test.client${timestamp}@test.com`)).toBeVisible();
    await expect(page.getByText('(555) 123-7890')).toBeVisible();
    
    // Step 8: Navigate through key modules
    const modules = ['Housing', 'Benefits', 'Legal', 'Jobs', 'AI Assistant'];
    
    for (const module of modules) {
      await page.getByRole('navigation').getByRole('link', { name: module, exact: true }).click();
      await expect(page.getByRole('main')).toBeVisible();
    }
    
    // Step 9: Return to Case Management and verify data persistence
    await page.getByRole('navigation').getByRole('link', { name: 'Case Management', exact: true }).click();
    await expect(page).toHaveURL(/case-management/);
    await expect(page.getByText(`Test Client${timestamp}`)).toBeVisible();
    await expect(page.getByText(`test.client${timestamp}@test.com`)).toBeVisible();
    
    // Verify client actions are available
    const clientRow = page.locator('tbody tr').filter({ hasText: `Test Client${timestamp}` });
    await expect(clientRow).toBeVisible();
    await expect(clientRow.getByRole('button', { name: 'View Dashboard' })).toBeVisible();
    await expect(clientRow.getByRole('button', { name: 'View Profile' })).toBeVisible();
  });
  
  test('System navigation and responsiveness', async ({ page }) => {
    await page.goto('/');
    
    // Test basic navigation
    const navigationModules = [
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
    
    // Verify all navigation links are present
    for (const module of navigationModules) {
      await expect(page.getByRole('navigation').getByRole('link', { name: module })).toBeVisible();
    }
    
    // Test responsive design
    await page.setViewportSize({ width: 1200, height: 800 });
    await expect(page.getByRole('navigation')).toBeVisible();
    
    await page.setViewportSize({ width: 768, height: 600 });
    await expect(page.getByRole('main')).toBeVisible();
  });
});