# Case Management Suite - E2E Testing Suite

## Overview
This directory contains comprehensive End-to-End (E2E) tests for the Case Management Suite, focusing on the **Maria Santos Case Manager Day** scenario as specified.

## Testing Framework
- **Framework**: Playwright v1.44+
- **Language**: JavaScript
- **Test Runner**: @playwright/test
- **Browser Support**: Chromium, Firefox, WebKit

## Test Structure

### 1. Basic Navigation Tests (`basic-navigation.spec.js`)
**Status**: ✅ PASSING (All 5 tests)
- Application loads and displays main dashboard
- Navigation to different modules works
- Smart Dashboard displays basic structure
- Housing Search form functionality
- AI Chat interface verification

### 2. Comprehensive Maria Santos Tests (`case-manager-day-comprehensive.spec.js`)
**Status**: ⚠️ PARTIALLY PASSING 
**Focus**: Complete workflow simulation for Maria Santos case management
- Morning workflow (9:00 AM - 12:00 PM)
- Client profile management
- Priority alert system
- AI Assistant consultation
- Housing search with background-friendly filters
- Legal services navigation
- Benefits coordination
- Task management and case notes

### 3. Focused Maria Santos Tests (`maria-santos-focused.spec.js`)
**Status**: ⚠️ NEEDS DATA SETUP
**Focus**: Specific Maria Santos workflows
- Morning workflow with all platform features
- Data integrity verification
- Priority alert system testing

## Test Scenario: Maria Santos Case Manager Day

### Client Background
**Maria Santos, 34** - High-need client requiring coordinated services:
- ✅ 18 months clean from addiction
- ✅ Recently released from transitional housing (30 days to find permanent housing)
- ✅ Expungement hearing scheduled next week
- ✅ Last employment: restaurant server (2019)
- ✅ Currently on SNAP, applying for Medicaid
- ✅ Has transportation (bus pass)
- ✅ Motivated but overwhelmed by multiple deadlines

### Current Challenges Covered in Tests
1. **Housing**: Must find permanent housing in 30 days
2. **Legal**: Expungement hearing next Tuesday, needs documentation
3. **Employment**: Needs job to qualify for housing programs
4. **Benefits**: Medicaid application incomplete
5. **Mental Health**: Anxiety about upcoming deadlines

## Test Execution

### Run All Tests
```bash
npx playwright test --reporter=line
```

### Run Specific Test Suite
```bash
npx playwright test basic-navigation.spec.js --reporter=line
npx playwright test maria-santos-focused.spec.js --reporter=line
npx playwright test case-manager-day-comprehensive.spec.js --reporter=line
```

### Run with UI Mode
```bash
npx playwright test --ui
```

### Run in Headed Mode (Visual)
```bash
npx playwright test --headed
```

### Debug Mode
```bash
npx playwright test --debug
```

## Application Requirements for Testing

### Backend Services
- **Backend**: http://localhost:8000 (FastAPI server)
- **Frontend**: http://localhost:5174 (Vite dev server)

### Test Data Requirements
- Maria Santos client data must be available in system
- Sample case management data
- Priority alerts system active
- AI Assistant configured

## Test Results Summary

### ✅ WORKING FEATURES
1. **Application Navigation**: All major modules accessible
2. **Dashboard Display**: Main dashboard loads with proper structure
3. **Smart Dashboard**: Priority alerts and AI reminders display
4. **Housing Search**: Form functionality and search execution
5. **AI Chat Interface**: UI loads and quick actions available
6. **Module Navigation**: All service modules accessible

### ⚠️ AREAS NEEDING ATTENTION
1. **Backend Data Connection**: Some tests fail due to data loading issues
2. **Maria Santos Data**: Client profile data may need proper seeding
3. **API Responses**: Some backend endpoints may need configuration
4. **Selector Stability**: Some UI elements need more stable selectors

### 🔧 RECOMMENDED FIXES
1. Ensure backend services are running during tests
2. Verify Maria Santos test data is properly loaded
3. Add test data seeding scripts
4. Implement more resilient selectors with data-testid attributes
5. Add API mocking for consistent test results

## Key Test Assertions Verified

### Dashboard Functionality
- ✅ Case Management Suite loads properly
- ✅ Service modules are accessible
- ✅ Navigation works between all pages

### Maria Santos Workflow
- ✅ Smart Dashboard shows priority alerts
- ✅ AI Assistant loads with contextual quick actions
- ✅ Housing search accepts criteria and executes
- ✅ Legal services page accessible
- ✅ Benefits module navigation works

### Form Interactions
- ✅ Housing search form accepts input
- ✅ AI chat interface allows message typing
- ✅ Background-friendly filters functional

## Maintenance Notes

### Regular Test Updates
- Update selectors if UI changes
- Verify test data remains consistent
- Add new test cases for new features
- Monitor test execution times

### CI/CD Integration
- Tests are configured for CI environments
- Background services need to be started
- Test reports are generated in HTML format
- Screenshots and videos captured on failures

## Contact Information
For questions about test implementation or debugging:
- Review Playwright documentation: https://playwright.dev
- Check test artifacts in test-results/ directory
- Use --ui mode for interactive debugging

---
**Last Updated**: $(date)
**Test Coverage**: Core navigation and basic workflows verified
**Status**: Framework established, ready for production testing