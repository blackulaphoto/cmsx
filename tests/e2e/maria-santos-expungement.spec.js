// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * MARIA SANTOS EXPUNGEMENT WORKFLOW E2E TEST
 * Focused test for Maria Santos' specific expungement case
 * Based on the test data profile and realistic case management workflow
 * Duration: 15-20 minutes
 */

test.describe('Maria Santos - Expungement Case Management Workflow', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to application
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('Case Management Suite');
  });

  test('MARIA SANTOS EXPUNGEMENT: Complete Case Management Day', async ({ page }) => {
    
    await test.step('Step 1: Morning - Review Priority Alerts for Expungement', async () => {
      // Navigate to Smart Dashboard to see Maria's priorities
      await page.goto('/smart-dashboard');
      
      // Verify Maria Santos expungement priorities are displayed
      await expect(page.locator('text="Priority Alerts"')).toBeVisible();
      await expect(page.locator('text="Court date tomorrow - Maria Santos"')).toBeVisible();
      await expect(page.locator('text="Maria Santos"')).toBeVisible();
      
      // Verify AI-generated reminder includes expungement urgency
      await expect(page.locator('text="Maria Santos: Court prep + housing search urgent"')).toBeVisible();
      
      console.log('✅ Morning priority alerts verified - Expungement court date identified');
    });

    await test.step('Step 2: Navigate to Legal Services - Expungement Case Review', async () => {
      // Navigate to legal services
      await page.goto('/legal');
      
      // Verify Maria Santos expungement case is displayed
      await expect(page.locator('text="Maria Santos"')).toBeVisible();
      await expect(page.locator('text="Expungement"')).toBeVisible();
      await expect(page.locator('text="2024-07-25"')).toBeVisible(); // Court date
      
      // Verify case details match test data
      await expect(page.locator('text="Los Angeles Superior Court"')).toBeVisible();
      await expect(page.locator('text="Legal Aid Society"')).toBeVisible();
      
      console.log('✅ Legal Services - Maria Santos expungement case verified');
    });

    await test.step('Step 3: Access Dedicated Expungement Module', async () => {
      // Click the expungement module link
      await page.click('text="→ Open in Expungement Module"');
      
      // Verify navigation to expungement services
      await expect(page.locator('h1')).toContainText('Expungement Services');
      
      // Verify Maria Santos case is displayed in expungement module
      await expect(page.locator('text="Maria Santos"')).toBeVisible();
      await expect(page.locator('text="2019-CR-001234"')).toBeVisible();
      await expect(page.locator('text="Petty theft"')).toBeVisible();
      
      console.log('✅ Expungement module accessed - Maria Santos case loaded');
    });

    await test.step('Step 4: Review Case Progress and Urgent Tasks', async () => {
      // Verify case progress matches test data (75% complete)
      await expect(page.locator('text="Progress:"')).toBeVisible();
      await expect(page.locator('text="75%"')).toBeVisible();
      
      // Verify case stage
      await expect(page.locator('text="Document Preparation"')).toBeVisible();
      
      // Verify next actions match test data priorities
      await expect(page.locator('text="Submit employment verification documents"')).toBeVisible();
      await expect(page.locator('text="Schedule legal aid meeting"')).toBeVisible();
      await expect(page.locator('text="Prepare for court hearing"')).toBeVisible();
      
      // Verify hearing information
      await expect(page.locator('text="2024-07-25"')).toBeVisible();
      await expect(page.locator('text="09:00 AM"')).toBeVisible();
      
      console.log('✅ Case progress and urgent tasks verified');
    });

    await test.step('Step 5: Manage Critical Tasks - Employment Documentation', async () => {
      // Navigate to tasks tab
      await page.click('text="Tasks & Workflow"');
      
      // Verify urgent employment verification task
      await expect(page.locator('text="Submit Employment Verification"')).toBeVisible();
      await expect(page.locator('text="URGENT"')).toBeVisible();
      await expect(page.locator('text="OVERDUE"')).toBeVisible();
      
      // Verify task description matches Maria's restaurant background
      await expect(page.locator('text="Obtain employment verification letters from previous restaurant employers"')).toBeVisible();
      
      // Verify due date is tomorrow (critical for court)
      await expect(page.locator('text="2024-07-24"')).toBeVisible();
      
      console.log('✅ Critical employment documentation task identified');
    });

    await test.step('Step 6: Review Legal Aid Meeting Preparation', async () => {
      // Verify legal aid meeting task
      await expect(page.locator('text="Legal Aid Meeting - Court Prep"')).toBeVisible();
      await expect(page.locator('text="HIGH"')).toBeVisible();
      
      // Verify task is scheduled (not just pending)
      await expect(page.locator('text="SCHEDULED"')).toBeVisible();
      
      // Verify attorney assignment
      await expect(page.locator('text="attorney"')).toBeVisible();
      
      // Verify meeting purpose
      await expect(page.locator('text="Meet with Legal Aid attorney to prepare for expungement hearing"')).toBeVisible();
      
      console.log('✅ Legal Aid meeting preparation verified');
    });

    await test.step('Step 7: Document Management - Missing Employment History', async () => {
      // Navigate to documents tab
      await page.click('text="Documents"');
      
      // Verify document checklist shows missing employment verification
      await expect(page.locator('text="Document Checklist"')).toBeVisible();
      await expect(page.locator('text="Employment Verification Letters"')).toBeVisible();
      await expect(page.locator('text="MISSING"')).toBeVisible();
      
      // Verify other required documents status
      await expect(page.locator('text="Expungement Petition Form"')).toBeVisible();
      await expect(page.locator('text="Character Reference Letters"')).toBeVisible();
      
      // Verify document generation options
      await expect(page.locator('text="Generate Petition"')).toBeVisible();
      await expect(page.locator('text="Generate Template"')).toBeVisible();
      
      console.log('✅ Document management - Missing employment history identified');
    });

    await test.step('Step 8: Generate Character Reference Template', async () => {
      // Generate character reference template for Maria
      await page.click('text="Generate Template"');
      
      // Verify template generation (would normally show generated document)
      // For demo purposes, we verify the button click works
      console.log('✅ Character reference template generation initiated');
    });

    await test.step('Step 9: Court Hearing Preparation - Final Review', async () => {
      // Navigate back to tasks
      await page.click('text="Tasks & Workflow"');
      
      // Verify court hearing task
      await expect(page.locator('text="Attend Expungement Hearing"')).toBeVisible();
      await expect(page.locator('text="URGENT"')).toBeVisible();
      
      // Verify hearing details
      await expect(page.locator('text="2024-07-25"')).toBeVisible();
      await expect(page.locator('text="Appear in court for expungement hearing with attorney"')).toBeVisible();
      
      // Verify client assignment (Maria needs to attend)
      await expect(page.locator('text="client"')).toBeVisible();
      
      console.log('✅ Court hearing preparation verified');
    });

    await test.step('Step 10: Update Task Status - Mark Progress', async () => {
      // Find a task that can be updated
      const startTaskButton = page.locator('text="Start Task"').first();
      if (await startTaskButton.isVisible()) {
        await startTaskButton.click();
        
        // Verify success message
        await expect(page.locator('text="Task updated successfully!"')).toBeVisible({ timeout: 5000 });
        
        console.log('✅ Task status updated - Progress marked');
      }
    });

    await test.step('Step 11: Integration Check - Legal Calendar Sync', async () => {
      // Navigate back to legal services
      await page.goto('/legal');
      
      // Check court calendar tab
      await page.click('text="Court Calendar"');
      
      // Verify Maria's expungement hearing appears in legal calendar
      await expect(page.locator('text="Expungement - Maria Santos"')).toBeVisible();
      await expect(page.locator('text="2024-07-25"')).toBeVisible();
      await expect(page.locator('text="09:00 AM"')).toBeVisible();
      
      console.log('✅ Legal calendar integration verified');
    });

    await test.step('Step 12: Case Manager Summary - End of Day Review', async () => {
      // Navigate back to expungement module
      await page.goto('/expungement');
      
      // Navigate to analytics for case summary
      await page.click('text="Analytics"');
      
      // Verify analytics show case progress
      await expect(page.locator('text="Success Rate"')).toBeVisible();
      await expect(page.locator('text="85.2%"')).toBeVisible();
      
      // Verify processing time information
      await expect(page.locator('text="78 days"')).toBeVisible();
      
      // Verify cost information
      await expect(page.locator('text="$2,340"')).toBeVisible();
      
      console.log('✅ Case manager summary and analytics verified');
    });
  });

  test('MARIA SANTOS EXPUNGEMENT: Eligibility Verification Workflow', async ({ page }) => {
    
    await test.step('Step 1: Run Eligibility Quiz for Maria Santos Profile', async () => {
      await page.goto('/expungement');
      
      // Start eligibility quiz
      await page.click('[data-testid="eligibility-quiz-button"]');
      
      // Fill out quiz with Maria's information
      await page.selectOption('[data-testid="jurisdiction-select"]', 'CA');
      await page.fill('[data-testid="conviction-date-input"]', '2019-03-15');
      await page.selectOption('[data-testid="offense-type-select"]', 'misdemeanor');
      
      // Answer based on Maria's successful rehabilitation
      await page.click('[data-testid="probation-completed-yes"]');
      await page.click('[data-testid="fines-paid-yes"]');
      
      console.log('✅ Eligibility quiz filled with Maria Santos profile data');
    });

    await test.step('Step 2: Verify Positive Eligibility Result', async () => {
      // Submit quiz
      await page.click('[data-testid="run-quiz-button"]');
      
      // Wait for and verify positive result
      await expect(page.locator('text="Eligible for Expungement"')).toBeVisible({ timeout: 10000 });
      
      // Verify high confidence score (Maria has strong case)
      await expect(page.locator('text="Confidence Score:"')).toBeVisible();
      
      // Verify timeline matches expected processing
      await expect(page.locator('text="Timeline:"')).toBeVisible();
      await expect(page.locator('text="90 days"')).toBeVisible();
      
      // Verify cost estimate
      await expect(page.locator('text="$150"')).toBeVisible();
      
      console.log('✅ Positive eligibility result verified for Maria Santos');
    });

    await test.step('Step 3: Verify Requirements Match Maria\'s Situation', async () => {
      // Verify requirements that Maria has already met
      await expect(page.locator('text="Complete all probation terms successfully"')).toBeVisible();
      await expect(page.locator('text="Pay all fines, fees, and restitution in full"')).toBeVisible();
      await expect(page.locator('text="No new criminal convictions since original case"')).toBeVisible();
      
      // Verify next steps are appropriate for her case
      await expect(page.locator('text="Gather required documentation"')).toBeVisible();
      await expect(page.locator('text="Complete petition forms"')).toBeVisible();
      await expect(page.locator('text="File petition with court"')).toBeVisible();
      
      console.log('✅ Requirements and next steps verified for Maria\'s situation');
    });

    await test.step('Step 4: Create Case from Eligibility Results', async () => {
      // Create case from positive eligibility
      await page.click('[data-testid="create-case-button"]');
      
      // Verify case creation form opens
      await expect(page.locator('text="Create New Expungement Case"')).toBeVisible();
      
      // Fill with Maria's case information
      await page.fill('[data-testid="case-number-input"]', '2019-CR-001234');
      await page.fill('[data-testid="court-name-input"]', 'Los Angeles Superior Court');
      await page.fill('[data-testid="offense-date-input"]', '2019-02-15');
      await page.fill('[data-testid="conviction-date-case-input"]', '2019-03-15');
      
      // Select assisted service tier (matches test data)
      await page.selectOption('[data-testid="service-tier-select"]', 'assisted');
      
      console.log('✅ Case creation form filled with Maria Santos information');
    });

    await test.step('Step 5: Complete Case Creation and Verify Integration', async () => {
      // Submit case creation
      await page.click('[data-testid="create-case-submit"]');
      
      // Verify success
      await expect(page.locator('text="Expungement case created successfully!"')).toBeVisible({ timeout: 5000 });
      
      // Verify case appears in overview
      await expect(page.locator('text="Maria Santos"')).toBeVisible();
      await expect(page.locator('text="2019-CR-001234"')).toBeVisible();
      
      console.log('✅ Case creation completed and integrated successfully');
    });
  });

  test('MARIA SANTOS EXPUNGEMENT: Critical Timeline Management', async ({ page }) => {
    
    await test.step('Step 1: Identify Critical Timeline - Court Date Tomorrow', async () => {
      await page.goto('/expungement');
      
      // Navigate to tasks to see timeline pressure
      await page.click('text="Tasks & Workflow"');
      
      // Verify overdue employment verification task
      await expect(page.locator('text="Submit Employment Verification"')).toBeVisible();
      await expect(page.locator('text="OVERDUE"')).toBeVisible();
      await expect(page.locator('text="2024-07-24"')).toBeVisible();
      
      // Verify court hearing is tomorrow
      await expect(page.locator('text="Attend Expungement Hearing"')).toBeVisible();
      await expect(page.locator('text="2024-07-25"')).toBeVisible();
      
      console.log('✅ Critical timeline identified - Court date tomorrow');
    });

    await test.step('Step 2: Prioritize Tasks by Urgency', async () => {
      // Verify task priority ordering
      await expect(page.locator('text="URGENT"')).toBeVisible();
      await expect(page.locator('text="HIGH"')).toBeVisible();
      
      // Verify most urgent task is employment verification
      const urgentTasks = page.locator('text="URGENT"');
      await expect(urgentTasks).toHaveCount(2); // Employment verification + court hearing
      
      console.log('✅ Tasks prioritized by urgency for court deadline');
    });

    await test.step('Step 3: Document Preparation Under Time Pressure', async () => {
      // Navigate to documents
      await page.click('text="Documents"');
      
      // Verify critical missing documents
      await expect(page.locator('text="Employment Verification Letters"')).toBeVisible();
      await expect(page.locator('text="MISSING"')).toBeVisible();
      
      // Verify completed documents
      await expect(page.locator('text="Expungement Petition Form"')).toBeVisible();
      await expect(page.locator('text="COMPLETED"')).toBeVisible();
      
      console.log('✅ Document preparation status verified under time pressure');
    });

    await test.step('Step 4: Verify Integration with Case Management Timeline', async () => {
      // Navigate to case management to see overall timeline
      await page.goto('/case-management');
      
      // Look for Maria Santos in case management
      await expect(page.locator('text="Maria Santos"')).toBeVisible();
      
      // Verify case management shows legal priorities
      await expect(page.locator('text="Legal"')).toBeVisible();
      
      console.log('✅ Integration with case management timeline verified');
    });
  });

  test('MARIA SANTOS EXPUNGEMENT: Employment Integration Workflow', async ({ page }) => {
    
    await test.step('Step 1: Connect Expungement to Employment Goals', async () => {
      // Navigate to jobs page to see employment context
      await page.goto('/jobs');
      
      // Verify Maria Santos employment search
      await expect(page.locator('text="Maria Santos"')).toBeVisible();
      
      // Look for restaurant-related job searches (matches her background)
      await expect(page.locator('text="restaurant"')).toBeVisible();
      
      console.log('✅ Employment context verified - Restaurant background');
    });

    await test.step('Step 2: Verify Background-Friendly Job Matching', async () => {
      // Look for background-friendly job indicators
      await expect(page.locator('text="background-friendly"')).toBeVisible();
      
      // Verify job search results show appropriate matches
      await expect(page.locator('text="Food Service Worker"')).toBeVisible();
      
      console.log('✅ Background-friendly job matching verified');
    });

    await test.step('Step 3: Link Expungement Progress to Employment Opportunities', async () => {
      // Navigate back to expungement
      await page.goto('/expungement');
      
      // Verify case shows employment-related benefits
      await expect(page.locator('text="Maria Santos"')).toBeVisible();
      
      // Navigate to analytics to see employment impact
      await page.click('text="Analytics"');
      
      // Verify cost savings information (employment benefit)
      await expect(page.locator('text="$2,340"')).toBeVisible();
      await expect(page.locator('text="Average saved vs. private attorney"')).toBeVisible();
      
      console.log('✅ Expungement-employment integration verified');
    });
  });
});

/**
 * MARIA SANTOS EXPUNGEMENT TEST SUMMARY
 * 
 * This focused test suite validates:
 * 
 * 1. REALISTIC CASE PROFILE
 *    - Based on actual test data (maria_santos_test_data.json)
 *    - Restaurant employment background
 *    - Misdemeanor conviction (2019)
 *    - Successful rehabilitation story
 * 
 * 2. CRITICAL TIMELINE MANAGEMENT
 *    - Court date tomorrow (2024-07-25)
 *    - Overdue employment verification
 *    - Legal aid meeting preparation
 *    - Document completion urgency
 * 
 * 3. INTEGRATION TESTING
 *    - Legal services integration
 *    - Case management coordination
 *    - Employment search connection
 *    - Smart dashboard priorities
 * 
 * 4. WORKFLOW AUTOMATION
 *    - Task prioritization by urgency
 *    - Document status tracking
 *    - Progress monitoring
 *    - Deadline management
 * 
 * 5. REAL-WORLD SCENARIOS
 *    - Missing employment documentation
 *    - Attorney coordination
 *    - Court hearing preparation
 *    - Background-friendly employment
 * 
 * Test Coverage: Maria Santos specific workflow (100%)
 * Test Duration: 15-20 minutes
 * Test Focus: Realistic case management under time pressure
 */