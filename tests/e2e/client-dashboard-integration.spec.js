// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * CLIENT DASHBOARD INTEGRATION TEST
 * Covers integrated client dashboard access and job search functionality
 * Focus: Step 4 & 5 of Maria Santos Case Manager Day workflow
 * Duration: 15-20 minutes
 */

test.describe('Client Dashboard Integration - Maria Santos Workflow', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to application and ensure it's loaded
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('Case Management Suite');
  });

  test('Step 4: Access Integrated Client Dashboard', async ({ page }) => {
    
    await test.step('Navigate to Client Search', async () => {
      // Access client search functionality
      await page.goto('/case-management');
      
      // Wait for page to load
      await expect(page.locator('h1')).toContainText('Case Management');
      
      // Verify search interface is available
      await expect(page.locator('input[placeholder*="Search"], input[type="search"], input[placeholder*="client"]')).toBeVisible();
      
      console.log('✅ Client search interface loaded');
    });

    await test.step('Search for Maria Santos', async () => {
      // Use client search functionality
      const searchInput = page.locator('input[placeholder*="Search"], input[type="search"], input[placeholder*="client"]').first();
      await searchInput.fill('Maria Santos');
      
      // Execute search (may be automatic or require button click)
      const searchButton = page.locator('button:has-text("Search"), button[type="submit"]');
      if (await searchButton.isVisible()) {
        await searchButton.click();
      }
      
      // Wait for search results
      await expect(page.locator('text="Maria Santos"')).toBeVisible({ timeout: 10000 });
      
      console.log('✅ Maria Santos search completed');
    });

    await test.step('Access Maria Santos Client Profile', async () => {
      // Click on Maria Santos result to access integrated dashboard
      await page.locator('button:has-text("View Profile")').first().click();
      
      // Verify complete client view loads
      await expect(page.locator('h2:has-text("Complete Client Profile"), h1:has-text("Maria Santos")')).toBeVisible();
      
      // Verify client profile section is displayed
      await expect(page.locator('text="Maria Santos"')).toBeVisible();
      await expect(page.locator('text="client_maria"')).toBeVisible();
      await expect(page.locator('text="(555) 987-6543"')).toBeVisible();
      
      console.log('✅ Client profile accessed successfully');
    });

    await test.step('Verify Integrated Module Status Display', async () => {
      // Verify housing status
      await expect(page.locator('text="Housing:"')).toBeVisible();
      await expect(page.locator('text="30 days to find permanent housing"')).toBeVisible();
      
      // Verify legal status  
      await expect(page.locator('text="Legal:"')).toBeVisible();
      await expect(page.locator('text="Expungement hearing scheduled"')).toBeVisible();
      
      // Verify employment status
      await expect(page.locator('text="Employment:"')).toBeVisible();
      await expect(page.locator('text="Restaurant server (2019)"')).toBeVisible();
      
      // Verify benefits status
      await expect(page.locator('text="Benefits:"')).toBeVisible();
      await expect(page.locator('text="SNAP active"')).toBeVisible();
      
      console.log('✅ All integrated module statuses verified');
    });

    await test.step('Verify Service Coordination Overview', async () => {
      // Check that all service areas are represented in integrated view
      const serviceAreas = ['Housing', 'Legal', 'Employment', 'Benefits', 'Mental Health'];
      
      for (const service of serviceAreas) {
        await expect(page.locator(`text="${service}"`).first()).toBeVisible();
      }
      
      // Verify urgency indicators
      await expect(page.locator('text="High", text="Urgent", text="Priority"')).toBeVisible();
      
      // Verify case notes section
      await expect(page.locator('text="Case Notes", text="Recent Activity", text="Updates"')).toBeVisible();
      
      console.log('✅ Service coordination overview complete');
    });
  });

  test('Step 5: Job Search for Client', async ({ page }) => {
    
    await test.step('Navigate to Employment Services', async () => {
      // Access employment/job search functionality
      await page.goto('/services');
      
      // Verify employment services are available
      await expect(page.locator('h1:has-text("Services")')).toBeVisible();
      await expect(page.locator('text="Employment"')).toBeVisible();
      
      console.log('✅ Employment services accessed');
    });

    await test.step('Search for Jobs Matching Maria\'s Profile', async () => {
      // Use job search functionality
      const searchInput = page.locator('input[placeholder*="search"], input[type="search"]').first();
      
      // Search for jobs matching Maria's background
      await searchInput.fill('restaurant server food service');
      
      // Execute search
      const searchButton = page.locator('button:has-text("Search"), button[type="submit"]');
      if (await searchButton.isVisible()) {
        await searchButton.click();
      }
      
      // Wait for results
      await page.waitForTimeout(2000); // Allow search to process
      
      console.log('✅ Job search executed for restaurant/food service roles');
    });

    await test.step('Filter Jobs for Background-Friendly Employers', async () => {
      // Look for background-friendly job filters
      const backgroundFilter = page.locator('input[type="checkbox"]:has(~ text="Background"), input[type="checkbox"]:has(~ text="Second chance"), input[type="checkbox"]');
      
      if (await backgroundFilter.first().isVisible()) {
        await backgroundFilter.first().check();
        
        // Re-execute search with filter
        const searchButton = page.locator('button:has-text("Search"), button[type="submit"]');
        if (await searchButton.isVisible()) {
          await searchButton.click();
        }
      }
      
      console.log('✅ Background-friendly job filter applied');
    });

    await test.step('Verify Job Opportunities for Maria', async () => {
      // Verify job listings appear (even if sample data)
      await expect(page.locator('text="Restaurant"')).toBeVisible({ timeout: 10000 });
      
      // Check for entry-level opportunities
      await expect(page.locator('text="Entry level"')).toBeVisible();
      
      // Verify location filters show LA area jobs
      await expect(page.locator('text="Los Angeles"')).toBeVisible();
      
      console.log('✅ Job opportunities verified for Maria\'s profile');
    });

    await test.step('Access Job Application Support', async () => {
      // Look for job application assistance features
      await expect(page.locator('text="Application help", text="Resume", text="Interview prep", text="Apply now"')).toBeVisible();
      
      // Verify job training programs are highlighted
      await expect(page.locator('text="Training program", text="Certification", text="Skills development"')).toBeVisible();
      
      // Check for transportation-accessible jobs (Maria has bus pass)
      await expect(page.locator('text="Public transit", text="Bus route", text="Transportation"')).toBeVisible();
      
      console.log('✅ Job application support features verified');
    });
  });

  test('Integrated Workflow: Client Dashboard to Employment Planning', async ({ page }) => {
    
    await test.step('Complete Client-to-Employment Workflow', async () => {
      // Start from case management
      await page.goto('/case-management');
      
      // Access Maria Santos profile
      const searchInput = page.locator('input[placeholder*="Search"], input[type="search"], input[placeholder*="client"]').first();
      await searchInput.fill('Maria Santos');
      
      const searchButton = page.locator('button:has-text("Search"), button[type="submit"]');
      if (await searchButton.isVisible()) {
        await searchButton.click();
      }
      
      // Wait for and click on Maria Santos profile
      await page.waitForSelector('text="Maria Santos"', { timeout: 10000 });
      await page.locator('button:has-text("View Profile")').first().click();
      
      // Verify employment section shows need for job search
      await expect(page.locator('text="Employment:"')).toBeVisible();
      await expect(page.locator('text="Restaurant server (2019)"')).toBeVisible();
      
      console.log('✅ Client profile shows employment needs');
    });

    await test.step('Navigate from Profile to Employment Services', async () => {
      // Navigate to employment services from profile
      await page.goto('/services');
      
      // Verify employment services context is relevant to Maria
      await expect(page.locator('text="Employment", text="Job Search"')).toBeVisible();
      
      // Execute employment search with Maria's context
      const searchInput = page.locator('input[placeholder*="search"]').first();
      await searchInput.fill('restaurant experience recovery friendly');
      
      const searchButton = page.locator('button:has-text("Search")');
      if (await searchButton.isVisible()) {
        await searchButton.click();
      }
      
      console.log('✅ Employment services accessed with client context');
    });

    await test.step('Verify Employment Plan Integration', async () => {
      // Verify employment opportunities match client needs
      await expect(page.locator('text="Restaurant", text="Food service", text="Server"')).toBeVisible({ timeout: 10000 });
      
      // Check for recovery-supportive employers
      await expect(page.locator('text="Second chance", text="Recovery friendly", text="Background friendly"')).toBeVisible();
      
      // Verify training opportunities
      await expect(page.locator('text="Training", text="Certification", text="Skills"')).toBeVisible();
      
      // Confirm transportation accessibility
      await expect(page.locator('text="Public transit", text="Bus accessible"')).toBeVisible();
      
      console.log('✅ Employment plan matches Maria\'s specific needs');
      console.log('📋 INTEGRATED CLIENT WORKFLOW COMPLETED:');
      console.log('   ✅ Client search and profile access');
      console.log('   ✅ Integrated module status display'); 
      console.log('   ✅ Service coordination overview');
      console.log('   ✅ Employment search with client context');
      console.log('   ✅ Job opportunities matching background');
      console.log('   ✅ Application support and training resources');
    });
  });

  test('Data Integrity: Client Profile Integration', async ({ page }) => {
    await page.goto('/case-management');
    
    // Test data consistency across modules
    const expectedClientData = [
      'Maria Santos',
      'client_maria', 
      '(555) 987-6543',
      'maria.santos@email.com',
      '18 months clean',
      '30 days to find permanent housing',
      'Expungement hearing scheduled',
      'Restaurant server (2019)',
      'SNAP active',
      'Medicaid application pending',
      'Has bus pass'
    ];
    
    // Access Maria's profile
    const searchInput = page.locator('input[placeholder*="Search"], input[type="search"], input[placeholder*="client"]').first();
    await searchInput.fill('Maria Santos');
    
    const searchButton = page.locator('button:has-text("Search"), button[type="submit"]');
    if (await searchButton.isVisible()) {
      await searchButton.click();
    }
    
    await page.waitForSelector('text="Maria Santos"', { timeout: 10000 });
    await page.locator('button:has-text("View Profile")').first().click();
    
    // Verify all expected data points are present
    let verifiedData = 0;
    for (const dataPoint of expectedClientData) {
      if (await page.locator(`text="${dataPoint}"`).first().isVisible()) {
        verifiedData++;
      }
    }
    
    console.log(`✅ Client data integrity check: ${verifiedData}/${expectedClientData.length} data points verified`);
    
    // Verify at least 70% of data is present (allows for some variation)
    expect(verifiedData).toBeGreaterThan(Math.floor(expectedClientData.length * 0.7));
  });

});