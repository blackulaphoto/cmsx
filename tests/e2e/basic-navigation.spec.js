// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * BASIC NAVIGATION TEST
 * Verifies core application functionality without dependencies
 * This test will work even if backend services are not fully running
 */

test.describe('Case Management Suite - Basic Navigation Tests', () => {

  test('Application loads and displays main dashboard', async ({ page }) => {
    // Navigate to the application
    await page.goto('/');
    
    // Verify main page elements load
    await expect(page).toHaveTitle(/Case Management Suite/);
    await expect(page.locator('h1')).toContainText('Case Management Suite');
    
    // Verify basic navigation elements are present
    await expect(page.locator('text="Available Services"')).toBeVisible();
    await expect(page.locator('text="Case Management"')).toBeVisible();
    await expect(page.locator('text="Housing Search"')).toBeVisible();
    
    console.log('✅ Main dashboard loaded successfully');
  });

  test('Navigation to different modules works', async ({ page }) => {
    await page.goto('/');
    
    // Test Case Management navigation
    await page.click('a[href="/case-management"]');
    await expect(page).toHaveURL(/.*case-management/);
    await expect(page.locator('h1')).toContainText('Case Management');
    
    // Test Smart Dashboard navigation
    await page.goto('/smart-dashboard');
    await expect(page).toHaveURL(/.*smart-dashboard/);
    await expect(page.locator('h1')).toContainText('Smart Daily Dashboard');
    
    // Test Housing Search navigation
    await page.goto('/housing');
    await expect(page).toHaveURL(/.*housing/);
    await expect(page.locator('h1')).toContainText('Housing Search');
    
    // Test AI Chat navigation
    await page.goto('/ai-chat');
    await expect(page).toHaveURL(/.*ai-chat/);
    await expect(page.locator('h1')).toContainText('AI Chat Assistant');
    
    // Test Benefits navigation
    await page.goto('/benefits');
    await expect(page).toHaveURL(/.*benefits/);
    await expect(page.locator('h1')).toContainText('Benefits');
    
    // Test Legal Services navigation
    await page.goto('/legal');
    await expect(page).toHaveURL(/.*legal/);
    await expect(page.locator('h1')).toContainText('Legal');
    
    // Test Services Directory navigation
    await page.goto('/services');
    await expect(page).toHaveURL(/.*services/);
    await expect(page.locator('h1')).toContainText('Services');
    
    console.log('✅ All module navigation verified');
  });

  test('Smart Dashboard displays basic structure', async ({ page }) => {
    await page.goto('/smart-dashboard');
    
    // Verify core dashboard sections are present
    await expect(page.locator('text="Smart Daily Dashboard"')).toBeVisible();
    await expect(page.locator('text="Priority Alerts"')).toBeVisible();
    await expect(page.locator('text="AI-Generated Reminders"')).toBeVisible();
    
    // Verify dashboard statistics are displayed
    await expect(page.locator('text="Today\'s Tasks"')).toBeVisible();
    await expect(page.locator('text="Completed"')).toBeVisible();
    await expect(page.locator('text="Urgent"')).toBeVisible();
    
    console.log('✅ Smart Dashboard structure verified');
  });

  test('Housing Search form is functional', async ({ page }) => {
    await page.goto('/housing');
    
    // Verify form elements are present
    await expect(page.locator('input[placeholder*="City"]')).toBeVisible();
    await expect(page.locator('input[placeholder*="rent"]')).toBeVisible();
    await expect(page.locator('select')).toBeVisible();
    await expect(page.locator('input[type="checkbox"]')).toBeVisible();
    
    // Test form interaction
    await page.fill('input[placeholder*="City"]', 'Los Angeles');
    await page.fill('input[placeholder*="rent"]', '1000');
    await page.check('input[type="checkbox"]');
    
    // Verify form can be submitted
    await page.click('button:has-text("Search Housing")');
    
    // Form submission should not cause errors (even if no results)
    await expect(page).toHaveURL(/.*housing/);
    
    console.log('✅ Housing Search form functionality verified');
  });

  test('AI Chat interface loads correctly', async ({ page }) => {
    await page.goto('/ai-chat');
    
    // Verify AI Chat interface elements
    await expect(page.locator('h1:has-text("AI Chat Assistant")')).toBeVisible();
    await expect(page.locator('text="Quick Actions"')).toBeVisible();
    await expect(page.locator('textarea')).toBeVisible();
    
    // Verify quick action buttons are present
    await expect(page.locator('button:has-text("Maria")').first()).toBeVisible();
    await expect(page.locator('button:has-text("restaurant")')).toBeVisible();
    
    // Test typing in chat interface
    await page.fill('textarea', 'Test message');
    await expect(page.locator('textarea')).toHaveValue('Test message');
    
    console.log('✅ AI Chat interface verified');
  });

});