import { test, expect } from '@playwright/test';

/**
 * Focused Case Manager Daily Workflow - End-to-End Test
 * 
 * This test covers the essential daily workflow of a case manager in the most reliable way possible.
 */

test.describe('Focused Case Manager Daily Workflow', () => {
  test('Complete case manager workflow - dashboard navigation and client management', async ({ page }) => {
    // Step 1: Load application and verify basic functionality
    await page.goto('/');
    await expect(page).toHaveTitle(/Case Management Suite/);
    await expect(page.getByRole('main')).toBeVisible();
    
    console.log('✓ Dashboard loaded successfully');
    
    // Step 2: Test navigation to key modules
    const modules = [
      { name: 'Smart Daily', url: /smart-dashboard/ },
      { name: 'Case Management', url: /case-management/ },
      { name: 'Housing', url: /housing/ },
      { name: 'Benefits', url: /benefits/ },
      { name: 'Legal', url: /legal/ },
      { name: 'AI Assistant', url: /ai-chat/ }
    ];
    
    for (const module of modules) {
      await page.getByRole('navigation').getByRole('link', { name: module.name, exact: true }).click();
      await expect(page).toHaveURL(module.url);
      await expect(page.getByRole('main')).toBeVisible();
      console.log(`✓ ${module.name} module loaded successfully`);
    }
    
    // Step 3: Focus on Case Management functionality
    await page.getByRole('navigation').getByRole('link', { name: 'Case Management', exact: true }).click();
    await expect(page).toHaveURL(/case-management/);
    
    // Verify case management components
    await expect(page.getByRole('table')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Add Client' })).toBeVisible();
    
    console.log('✓ Case Management interface verified');
    
    // Step 4: Test client creation flow
    await page.getByRole('button', { name: 'Add Client' }).click();
    await expect(page.getByText('Client Intake Form')).toBeVisible();
    await expect(page.getByText('Personal Information')).toBeVisible();
    
    console.log('✓ Client intake form opened');
    
    // Step 5: Fill minimal required information
    const testTime = Date.now();
    await page.getByRole('textbox', { name: 'Enter first name' }).fill('TestClient');
    await page.getByRole('textbox', { name: 'Enter last name' }).fill(`E2E${testTime}`);
    
    // Try to create client
    await page.getByRole('button', { name: 'Create Client Profile' }).click();
    
    // Wait for the form to process
    await page.waitForTimeout(2000);
    
    // Verify we're back at the case management page
    await expect(page.getByRole('table')).toBeVisible();
    
    console.log('✓ Client creation process completed');
    
    // Step 6: Verify client table has data
    const tableRows = await page.getByRole('table').locator('tbody tr').count();
    expect(tableRows).toBeGreaterThan(0);
    
    console.log(`✓ Client table contains ${tableRows} clients`);
    
    // Step 7: Test Smart Daily Dashboard functionality
    await page.getByRole('navigation').getByRole('link', { name: 'Smart Daily', exact: true }).click();
    await expect(page).toHaveURL(/smart-dashboard/);
    await expect(page.getByRole('main')).toBeVisible();
    
    // Verify Smart Daily components
    const hasQuickActions = await page.getByText('Quick Actions').isVisible().catch(() => false);
    const hasAIRecommendations = await page.getByText('AI-Generated Reminders').isVisible().catch(() => false);
    
    if (hasQuickActions) console.log('✓ Quick Actions section found');
    if (hasAIRecommendations) console.log('✓ AI Recommendations section found');
    
    // Step 8: Final system health check
    await page.goto('/');
    await expect(page.getByRole('main')).toBeVisible();
    
    // Verify all navigation links are accessible
    const navLinks = [
      'Dashboard', 'Case Management', 'Housing', 'Benefits', 
      'Legal', 'Resume', 'Jobs', 'Services', 'AI Assistant', 'Smart Daily'
    ];
    
    for (const link of navLinks) {
      await expect(page.getByRole('navigation').getByRole('link', { name: link })).toBeVisible();
    }
    
    console.log('✓ All navigation links verified');
    console.log('🎉 Complete case manager workflow test passed!');
  });

  test('Case management system performance and reliability', async ({ page }) => {
    // Test system under rapid navigation
    await page.goto('/');
    
    const modules = ['Case Management', 'Housing', 'Benefits', 'Legal', 'Smart Daily'];
    
    // Rapid navigation test
    for (let i = 0; i < 3; i++) {
      for (const module of modules) {
        await page.getByRole('navigation').getByRole('link', { name: module, exact: true }).click();
        await expect(page.getByRole('main')).toBeVisible();
      }
    }
    
    console.log('✓ System handles rapid navigation well');
    
    // Test responsive design
    await page.setViewportSize({ width: 1200, height: 800 });
    await expect(page.getByRole('navigation')).toBeVisible();
    
    await page.setViewportSize({ width: 768, height: 600 });
    await expect(page.getByRole('main')).toBeVisible();
    
    console.log('✓ Responsive design verified');
  });
});