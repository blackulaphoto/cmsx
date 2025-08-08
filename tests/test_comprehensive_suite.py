#!/usr/bin/env python3
"""
Comprehensive Testing Suite Runner
Orchestrates all testing phases and generates comprehensive reports
"""

import pytest
import sys
import json
import time
from datetime import datetime
from pathlib import Path
import logging
import subprocess
from typing import Dict, List, Any, Optional
import sqlite3

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveTestSuite:
    """Comprehensive testing suite orchestrator"""
    
    def __init__(self):
        self.test_results = {
            'data_integrity': {},
            'performance_indexing': {},
            'referential_integrity': {},
            'end_to_end_workflows': {},
            'summary': {}
        }
        
        self.test_phases = [
            {
                'name': 'Data Integrity Testing',
                'module': 'test_data_integrity.py',
                'description': 'Tests data consistency, validation, and integrity across all databases',
                'critical': True
            },
            {
                'name': 'Performance & Indexing Testing',
                'module': 'test_performance_indexing.py',
                'description': 'Tests database performance, query optimization, and indexing strategies',
                'critical': True
            },
            {
                'name': 'Referential Integrity Testing',
                'module': 'test_referential_integrity.py',
                'description': 'Tests foreign key relationships, cascade operations, and data consistency',
                'critical': True
            },
            {
                'name': 'End-to-End Workflow Testing',
                'module': 'test_end_to_end_workflows.py',
                'description': 'Tests complete business workflows across all modules',
                'critical': True
            }
        ]
        
        self.start_time = None
        self.end_time = None
    
    def check_system_prerequisites(self) -> Dict[str, bool]:
        """Check system prerequisites for testing"""
        prerequisites = {}
        
        # Check database files exist
        db_paths = [
            'databases/case_management.db',
            'databases/legal_cases.db',
            'databases/expungement.db',
            'databases/reminders.db',
            'databases/benefits_transport.db'
        ]
        
        for db_path in db_paths:
            prerequisites[f"Database: {db_path}"] = Path(db_path).exists()
        
        # Check API availability
        try:
            import requests
            response = requests.get('http://localhost:8000/health', timeout=5)
            prerequisites['API Server'] = response.status_code == 200
        except Exception:
            prerequisites['API Server'] = False
        
        # Check required Python packages
        required_packages = ['pytest', 'requests', 'sqlite3']
        for package in required_packages:
            try:
                __import__(package)
                prerequisites[f"Package: {package}"] = True
            except ImportError:
                prerequisites[f"Package: {package}"] = False
        
        return prerequisites
    
    def run_test_phase(self, phase: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test phase"""
        logger.info(f"🔄 Starting {phase['name']}")
        
        phase_start = time.time()
        
        try:
            # Run pytest for the specific module
            cmd = [
                sys.executable, '-m', 'pytest',
                f"tests/{phase['module']}",
                '-v',
                '--tb=short',
                '--json-report',
                f'--json-report-file=test-results/{phase["module"]}.json'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per phase
            )
            
            phase_end = time.time()
            duration = phase_end - phase_start
            
            # Parse results
            try:
                with open(f'test-results/{phase["module"]}.json', 'r') as f:
                    test_data = json.load(f)
                
                return {
                    'name': phase['name'],
                    'module': phase['module'],
                    'success': result.returncode == 0,
                    'duration': duration,
                    'tests_run': test_data.get('summary', {}).get('total', 0),
                    'tests_passed': test_data.get('summary', {}).get('passed', 0),
                    'tests_failed': test_data.get('summary', {}).get('failed', 0),
                    'tests_skipped': test_data.get('summary', {}).get('skipped', 0),
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'detailed_results': test_data
                }
            except Exception as e:
                logger.warning(f"Could not parse test results for {phase['name']}: {e}")
                
                return {
                    'name': phase['name'],
                    'module': phase['module'],
                    'success': result.returncode == 0,
                    'duration': duration,
                    'tests_run': 0,
                    'tests_passed': 0,
                    'tests_failed': 0,
                    'tests_skipped': 0,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'error': str(e)
                }
                
        except subprocess.TimeoutExpired:
            return {
                'name': phase['name'],
                'module': phase['module'],
                'success': False,
                'duration': 300,
                'error': 'Test phase timed out',
                'tests_run': 0,
                'tests_passed': 0,
                'tests_failed': 0,
                'tests_skipped': 0
            }
        except Exception as e:
            return {
                'name': phase['name'],
                'module': phase['module'],
                'success': False,
                'duration': time.time() - phase_start,
                'error': str(e),
                'tests_run': 0,
                'tests_passed': 0,
                'tests_failed': 0,
                'tests_skipped': 0
            }
    
    def generate_database_health_report(self) -> Dict[str, Any]:
        """Generate database health report"""
        health_report = {}
        
        db_paths = {
            'case_management': 'databases/case_management.db',
            'legal_cases': 'databases/legal_cases.db',
            'expungement': 'databases/expungement.db',
            'reminders': 'databases/reminders.db',
            'benefits_transport': 'databases/benefits_transport.db'
        }
        
        for db_name, db_path in db_paths.items():
            try:
                if Path(db_path).exists():
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # Get database size
                    file_size = Path(db_path).stat().st_size
                    
                    # Get table count
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                    table_count = cursor.fetchone()[0]
                    
                    # Get total record count (approximate)
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    total_records = 0
                    for table in tables:
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table}")
                            total_records += cursor.fetchone()[0]
                        except sqlite3.OperationalError:
                            continue
                    
                    # Check integrity
                    cursor.execute("PRAGMA integrity_check")
                    integrity_result = cursor.fetchone()[0]
                    
                    health_report[db_name] = {
                        'exists': True,
                        'size_bytes': file_size,
                        'size_mb': round(file_size / (1024 * 1024), 2),
                        'table_count': table_count,
                        'total_records': total_records,
                        'integrity_ok': integrity_result == 'ok'
                    }
                    
                    conn.close()
                else:
                    health_report[db_name] = {
                        'exists': False,
                        'error': 'Database file not found'
                    }
                    
            except Exception as e:
                health_report[db_name] = {
                    'exists': Path(db_path).exists(),
                    'error': str(e)
                }
        
        return health_report
    
    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all test phases and generate comprehensive report"""
        logger.info("🚀 Starting Comprehensive Testing Suite")
        
        self.start_time = datetime.now()
        
        # Check prerequisites
        logger.info("🔍 Checking system prerequisites")
        prerequisites = self.check_system_prerequisites()
        
        failed_prerequisites = [k for k, v in prerequisites.items() if not v]
        if failed_prerequisites:
            logger.warning(f"⚠️ Failed prerequisites: {failed_prerequisites}")
        
        # Generate database health report
        logger.info("🏥 Generating database health report")
        db_health = self.generate_database_health_report()
        
        # Create test results directory
        Path('test-results').mkdir(exist_ok=True)
        
        # Run each test phase
        phase_results = []
        for phase in self.test_phases:
            result = self.run_test_phase(phase)
            phase_results.append(result)
            
            if result['success']:
                logger.info(f"✅ {phase['name']} completed successfully")
            else:
                logger.error(f"❌ {phase['name']} failed")
                if phase.get('critical', False):
                    logger.error(f"💥 Critical test phase failed: {phase['name']}")
        
        self.end_time = datetime.now()
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        # Generate summary
        total_tests = sum(r['tests_run'] for r in phase_results)
        total_passed = sum(r['tests_passed'] for r in phase_results)
        total_failed = sum(r['tests_failed'] for r in phase_results)
        total_skipped = sum(r['tests_skipped'] for r in phase_results)
        
        successful_phases = sum(1 for r in phase_results if r['success'])
        
        summary = {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'total_duration_seconds': total_duration,
            'prerequisites': prerequisites,
            'database_health': db_health,
            'phases_run': len(phase_results),
            'phases_successful': successful_phases,
            'phases_failed': len(phase_results) - successful_phases,
            'total_tests': total_tests,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'total_skipped': total_skipped,
            'success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
            'overall_success': successful_phases == len(phase_results) and total_failed == 0
        }
        
        # Compile final report
        final_report = {
            'summary': summary,
            'phase_results': phase_results,
            'generated_at': datetime.now().isoformat(),
            'system_info': {
                'python_version': sys.version,
                'platform': sys.platform
            }
        }
        
        # Save comprehensive report
        report_filename = f"comprehensive_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(f'test-results/{report_filename}', 'w') as f:
            json.dump(final_report, f, indent=2)
        
        logger.info(f"📊 Comprehensive test report saved: {report_filename}")
        
        return final_report
    
    def print_summary_report(self, report: Dict[str, Any]):
        """Print a human-readable summary report"""
        summary = report['summary']
        
        print("\n" + "="*80)
        print("🧪 COMPREHENSIVE TESTING SUITE REPORT")
        print("="*80)
        
        print(f"📅 Test Run: {summary['start_time']} to {summary['end_time']}")
        print(f"⏱️  Duration: {summary['total_duration_seconds']:.2f} seconds")
        print(f"🎯 Overall Success: {'✅ PASS' if summary['overall_success'] else '❌ FAIL'}")
        
        print("\n📊 TEST STATISTICS:")
        print(f"   Phases Run: {summary['phases_run']}")
        print(f"   Phases Successful: {summary['phases_successful']}")
        print(f"   Phases Failed: {summary['phases_failed']}")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Tests Passed: {summary['total_passed']}")
        print(f"   Tests Failed: {summary['total_failed']}")
        print(f"   Tests Skipped: {summary['total_skipped']}")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        
        print("\n🏥 DATABASE HEALTH:")
        for db_name, health in summary['database_health'].items():
            if health.get('exists', False):
                status = "✅" if health.get('integrity_ok', False) else "⚠️"
                print(f"   {status} {db_name}: {health.get('size_mb', 0):.2f}MB, "
                      f"{health.get('table_count', 0)} tables, "
                      f"{health.get('total_records', 0)} records")
            else:
                print(f"   ❌ {db_name}: Not found")
        
        print("\n📋 PHASE RESULTS:")
        for result in report['phase_results']:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"   {status} {result['name']}: "
                  f"{result['tests_passed']}/{result['tests_run']} tests passed "
                  f"({result['duration']:.2f}s)")
        
        print("\n🔍 PREREQUISITES:")
        for prereq, status in summary['prerequisites'].items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {prereq}")
        
        print("\n" + "="*80)
        
        if summary['overall_success']:
            print("🎉 ALL TESTS PASSED! System is ready for production.")
        else:
            print("⚠️  SOME TESTS FAILED! Review the detailed report for issues.")
        
        print("="*80)

def main():
    """Main entry point for comprehensive testing"""
    suite = ComprehensiveTestSuite()
    
    try:
        report = suite.run_comprehensive_tests()
        suite.print_summary_report(report)
        
        # Exit with appropriate code
        if report['summary']['overall_success']:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Testing interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Comprehensive testing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()