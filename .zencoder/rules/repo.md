# Repository Rules - Case Management Suite

## Testing Framework
- **E2E Testing Framework**: Playwright
- **Backend Testing**: pytest (existing)
- **Test Location**: `tests/e2e/` directory for Playwright tests
- **Working E2E Tests**: 
  - `complete-case-manager-daily-workflow.spec.ts` - Comprehensive Maria Santos scenario
  - `focused-case-manager-workflow.spec.ts` - Core workflow validation (PASSING ✅)
- **Test Execution**: `npx playwright test tests/e2e/ --reporter=line`

## Application Configuration
- **Backend URL**: http://localhost:8000
- **Frontend URL**: http://localhost:5173 (Vite dev server)
- **Test Environment**: Local development with test database

## Test Data
- Maria Santos test client data available in `maria_santos_test_data.json`
- Test should use realistic case management workflows
- All tests must be deterministic and isolated