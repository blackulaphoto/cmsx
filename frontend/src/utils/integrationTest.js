/**
 * Frontend Integration Test Utility
 * 
 * This utility helps test frontend integration with the backend by:
 * 1. Monitoring console errors
 * 2. Tracking API calls and their status
 * 3. Detecting component crashes
 * 
 * Usage:
 * Import this utility in your component and call startMonitoring()
 * The results will be logged to the console and can be viewed in the browser
 */

class IntegrationTest {
  constructor() {
    this.errors = [];
    this.apiCalls = [];
    this.componentCrashes = [];
    this.isMonitoring = false;
    this.originalConsoleError = null;
    this.originalFetch = null;
    this.originalXHR = null;
  }

  /**
   * Start monitoring console errors, API calls, and component crashes
   */
  startMonitoring() {
    if (this.isMonitoring) return;
    this.isMonitoring = true;
    
    // Monitor console errors
    this.originalConsoleError = console.error;
    console.error = (...args) => {
      this.errors.push({
        timestamp: new Date().toISOString(),
        message: args.map(arg => 
          typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
        ).join(' '),
      });
      this.originalConsoleError.apply(console, args);
    };

    // Monitor fetch API calls
    this.originalFetch = window.fetch;
    window.fetch = async (...args) => {
      const url = args[0];
      const options = args[1] || {};
      const startTime = Date.now();
      
      try {
        const response = await this.originalFetch.apply(window, args);
        const endTime = Date.now();
        
        this.apiCalls.push({
          timestamp: new Date().toISOString(),
          url,
          method: options.method || 'GET',
          status: response.status,
          duration: endTime - startTime,
          success: response.ok,
        });
        
        return response;
      } catch (error) {
        const endTime = Date.now();
        
        this.apiCalls.push({
          timestamp: new Date().toISOString(),
          url,
          method: options.method || 'GET',
          error: error.message,
          duration: endTime - startTime,
          success: false,
        });
        
        throw error;
      }
    };

    // Monitor XMLHttpRequest API calls
    this.originalXHR = window.XMLHttpRequest.prototype.open;
    window.XMLHttpRequest.prototype.open = function(method, url) {
      this._integrationTestUrl = url;
      this._integrationTestMethod = method;
      this._integrationTestStartTime = Date.now();
      
      this.addEventListener('load', function() {
        const endTime = Date.now();
        const status = this.status;
        
        window.integrationTest.apiCalls.push({
          timestamp: new Date().toISOString(),
          url: this._integrationTestUrl,
          method: this._integrationTestMethod,
          status,
          duration: endTime - this._integrationTestStartTime,
          success: status >= 200 && status < 300,
        });
      });
      
      this.addEventListener('error', function(error) {
        const endTime = Date.now();
        
        window.integrationTest.apiCalls.push({
          timestamp: new Date().toISOString(),
          url: this._integrationTestUrl,
          method: this._integrationTestMethod,
          error: 'Network error',
          duration: endTime - this._integrationTestStartTime,
          success: false,
        });
      });
      
      return window.integrationTest.originalXHR.apply(this, arguments);
    };

    // Add global error handler for component crashes
    window.addEventListener('error', (event) => {
      this.componentCrashes.push({
        timestamp: new Date().toISOString(),
        message: event.message,
        source: event.filename,
        lineNumber: event.lineno,
        columnNumber: event.colno,
      });
    });

    // Add global unhandled rejection handler
    window.addEventListener('unhandledrejection', (event) => {
      this.componentCrashes.push({
        timestamp: new Date().toISOString(),
        message: event.reason?.message || 'Unhandled Promise Rejection',
        stack: event.reason?.stack,
      });
    });

    // Make this instance globally available
    window.integrationTest = this;
    
    console.log('🧪 Integration Test: Monitoring started');
  }

  /**
   * Stop monitoring and restore original functions
   */
  stopMonitoring() {
    if (!this.isMonitoring) return;
    
    console.error = this.originalConsoleError;
    window.fetch = this.originalFetch;
    window.XMLHttpRequest.prototype.open = this.originalXHR;
    
    this.isMonitoring = false;
    console.log('🧪 Integration Test: Monitoring stopped');
  }

  /**
   * Get a summary of all collected data
   */
  getSummary() {
    return {
      errors: this.errors,
      apiCalls: this.apiCalls,
      componentCrashes: this.componentCrashes,
      statistics: {
        totalErrors: this.errors.length,
        totalApiCalls: this.apiCalls.length,
        failedApiCalls: this.apiCalls.filter(call => !call.success).length,
        totalComponentCrashes: this.componentCrashes.length,
      }
    };
  }

  /**
   * Log the summary to the console
   */
  logSummary() {
    const summary = this.getSummary();
    
    console.group('🧪 Integration Test Summary');
    
    console.log(`Total Errors: ${summary.statistics.totalErrors}`);
    console.log(`Total API Calls: ${summary.statistics.totalApiCalls}`);
    console.log(`Failed API Calls: ${summary.statistics.failedApiCalls}`);
    console.log(`Component Crashes: ${summary.statistics.totalComponentCrashes}`);
    
    if (summary.errors.length > 0) {
      console.group('Console Errors');
      summary.errors.forEach(error => {
        console.log(`[${error.timestamp}] ${error.message}`);
      });
      console.groupEnd();
    }
    
    if (summary.apiCalls.filter(call => !call.success).length > 0) {
      console.group('Failed API Calls');
      summary.apiCalls.filter(call => !call.success).forEach(call => {
        console.log(`[${call.timestamp}] ${call.method} ${call.url} - ${call.status || call.error}`);
      });
      console.groupEnd();
    }
    
    if (summary.componentCrashes.length > 0) {
      console.group('Component Crashes');
      summary.componentCrashes.forEach(crash => {
        console.log(`[${crash.timestamp}] ${crash.message} (${crash.source}:${crash.lineNumber}:${crash.columnNumber})`);
      });
      console.groupEnd();
    }
    
    console.groupEnd();
    
    return summary;
  }

  /**
   * Clear all collected data
   */
  clearData() {
    this.errors = [];
    this.apiCalls = [];
    this.componentCrashes = [];
    console.log('🧪 Integration Test: Data cleared');
  }

  /**
   * Export the collected data as JSON
   */
  exportData() {
    const summary = this.getSummary();
    const dataStr = JSON.stringify(summary, null, 2);
    const dataUri = `data:application/json;charset=utf-8,${encodeURIComponent(dataStr)}`;
    
    const exportLink = document.createElement('a');
    exportLink.setAttribute('href', dataUri);
    exportLink.setAttribute('download', `integration-test-${new Date().toISOString()}.json`);
    document.body.appendChild(exportLink);
    exportLink.click();
    document.body.removeChild(exportLink);
    
    console.log('🧪 Integration Test: Data exported');
  }
}

// Create a singleton instance
const integrationTest = new IntegrationTest();

export default integrationTest;