#!/usr/bin/env python3
"""
Team Dashboard for Supervisors
Comprehensive team management and oversight for case management supervisors
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from .database_integration import SmartTaskDistributorIntegrated
from .notifications import NotificationService
from .models import ReminderDatabase

logger = logging.getLogger(__name__)

class TeamDashboard:
    """
    Supervisor dashboard for team management and oversight
    """
    
    def __init__(self, smart_distributor: SmartTaskDistributorIntegrated, 
                 notification_service: NotificationService):
        self.smart_distributor = smart_distributor
        self.notification_service = notification_service
        self.reminder_db = smart_distributor.reminder_db
        self.client_integration = smart_distributor.client_integration
        
        # Create team management tables
        self._create_team_tables()
    
    def _create_team_tables(self):
        """Create team management database tables"""
        if not self.reminder_db.connection:
            self.reminder_db.connect()
        
        team_tables = [
            """
            CREATE TABLE IF NOT EXISTS team_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supervisor_id TEXT NOT NULL,
                case_manager_id TEXT NOT NULL,
                team_name TEXT,
                assigned_date TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS team_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id TEXT NOT NULL,
                case_manager_id TEXT NOT NULL,
                metric_date TEXT NOT NULL,
                total_clients INTEGER DEFAULT 0,
                urgent_items INTEGER DEFAULT 0,
                completed_tasks INTEGER DEFAULT 0,
                overdue_tasks INTEGER DEFAULT 0,
                client_contacts INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0,
                satisfaction_score REAL DEFAULT 0,
                created_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS team_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT UNIQUE NOT NULL,
                supervisor_id TEXT NOT NULL,
                case_manager_id TEXT NOT NULL,
                client_id TEXT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                resolved_at TEXT,
                resolution_notes TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS performance_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id TEXT UNIQUE NOT NULL,
                supervisor_id TEXT NOT NULL,
                case_manager_id TEXT NOT NULL,
                review_period_start TEXT,
                review_period_end TEXT,
                overall_rating REAL,
                strengths TEXT,
                areas_for_improvement TEXT,
                goals_set TEXT,
                review_notes TEXT,
                created_at TEXT
            )
            """
        ]
        
        try:
            for table_sql in team_tables:
                self.reminder_db.connection.execute(table_sql)
            self.reminder_db.connection.commit()
            logger.info("Team management tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create team tables: {e}")
    
    def get_team_overview(self, supervisor_id: str) -> Dict[str, Any]:
        """Get comprehensive team overview for supervisor"""
        try:
            # Get team members
            team_members = self._get_team_members(supervisor_id)
            
            # Get team metrics
            team_metrics = self._calculate_team_metrics(supervisor_id, team_members)
            
            # Get active alerts
            active_alerts = self._get_active_alerts(supervisor_id)
            
            # Get performance insights
            performance_insights = self._get_performance_insights(supervisor_id, team_members)
            
            # Get workload distribution
            workload_distribution = self._get_workload_distribution(team_members)
            
            return {
                'supervisor_id': supervisor_id,
                'generated_at': datetime.now().isoformat(),
                'team_members': team_members,
                'team_metrics': team_metrics,
                'active_alerts': active_alerts,
                'performance_insights': performance_insights,
                'workload_distribution': workload_distribution,
                'recommendations': self._generate_team_recommendations(team_metrics, active_alerts)
            }
            
        except Exception as e:
            logger.error(f"Error generating team overview: {e}")
            return {'error': str(e)}
    
    def get_case_manager_detailed_view(self, supervisor_id: str, case_manager_id: str) -> Dict[str, Any]:
        """Get detailed view of specific case manager's performance"""
        try:
            # Verify supervisor has access to this case manager
            if not self._verify_supervisor_access(supervisor_id, case_manager_id):
                return {'error': 'Access denied'}
            
            # Get case manager's daily focus plan
            daily_plan = self.smart_distributor.get_enhanced_daily_focus_plan(case_manager_id)
            
            # Get case manager's clients
            clients = self.client_integration.get_case_manager_clients(case_manager_id)
            
            # Get performance metrics
            performance_metrics = self._get_case_manager_performance_metrics(case_manager_id)
            
            # Get recent activity
            recent_activity = self._get_recent_activity(case_manager_id)
            
            # Get client risk distribution
            risk_distribution = self._get_client_risk_distribution(clients)
            
            return {
                'case_manager_id': case_manager_id,
                'case_manager_name': self._get_case_manager_name(case_manager_id),
                'daily_plan': daily_plan,
                'client_count': len(clients),
                'performance_metrics': performance_metrics,
                'recent_activity': recent_activity,
                'risk_distribution': risk_distribution,
                'workload_assessment': self._assess_workload(daily_plan, clients),
                'recommendations': self._generate_case_manager_recommendations(performance_metrics, daily_plan)
            }
            
        except Exception as e:
            logger.error(f"Error getting case manager detailed view: {e}")
            return {'error': str(e)}
    
    def get_team_alerts(self, supervisor_id: str) -> List[Dict[str, Any]]:
        """Get all active alerts for the team"""
        try:
            cursor = self.reminder_db.connection.cursor()
            cursor.execute("""
                SELECT * FROM team_alerts 
                WHERE supervisor_id = ? AND status = 'active'
                ORDER BY severity DESC, created_at DESC
            """, (supervisor_id,))
            
            alerts = []
            for row in cursor.fetchall():
                alert_dict = dict(row)
                
                # Add context information
                if alert_dict['client_id']:
                    client_name = self.smart_distributor._get_client_name(alert_dict['client_id'])
                    alert_dict['client_name'] = client_name
                
                case_manager_name = self._get_case_manager_name(alert_dict['case_manager_id'])
                alert_dict['case_manager_name'] = case_manager_name
                
                alerts.append(alert_dict)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting team alerts: {e}")
            return []
    
    def create_team_alert(self, supervisor_id: str, case_manager_id: str, 
                         alert_type: str, severity: str, title: str, 
                         description: str, client_id: str = None) -> bool:
        """Create a new team alert"""
        try:
            cursor = self.reminder_db.connection.cursor()
            cursor.execute("""
                INSERT INTO team_alerts 
                (alert_id, supervisor_id, case_manager_id, client_id, alert_type, 
                 severity, title, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"alert_{datetime.now().timestamp()}",
                supervisor_id,
                case_manager_id,
                client_id,
                alert_type,
                severity,
                title,
                description,
                datetime.now().isoformat()
            ))
            
            self.reminder_db.connection.commit()
            logger.info(f"Created team alert: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating team alert: {e}")
            return False
    
    def resolve_team_alert(self, alert_id: str, resolution_notes: str) -> bool:
        """Resolve a team alert"""
        try:
            cursor = self.reminder_db.connection.cursor()
            cursor.execute("""
                UPDATE team_alerts 
                SET status = 'resolved', resolved_at = ?, resolution_notes = ?
                WHERE alert_id = ?
            """, (datetime.now().isoformat(), resolution_notes, alert_id))
            
            self.reminder_db.connection.commit()
            logger.info(f"Resolved team alert: {alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error resolving team alert: {e}")
            return False
    
    def get_team_performance_report(self, supervisor_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Generate comprehensive team performance report"""
        try:
            team_members = self._get_team_members(supervisor_id)
            
            report = {
                'supervisor_id': supervisor_id,
                'report_period': {'start': start_date, 'end': end_date},
                'generated_at': datetime.now().isoformat(),
                'team_summary': {},
                'individual_performance': {},
                'trends': {},
                'recommendations': []
            }
            
            # Calculate team-wide metrics
            total_clients = 0
            total_completed_tasks = 0
            total_overdue_tasks = 0
            total_client_contacts = 0
            
            for member in team_members:
                case_manager_id = member['case_manager_id']
                
                # Get individual performance
                individual_metrics = self._get_performance_metrics_for_period(
                    case_manager_id, start_date, end_date
                )
                
                report['individual_performance'][case_manager_id] = {
                    'case_manager_name': member['case_manager_name'],
                    'metrics': individual_metrics,
                    'rating': self._calculate_performance_rating(individual_metrics)
                }
                
                # Aggregate to team totals
                total_clients += individual_metrics.get('total_clients', 0)
                total_completed_tasks += individual_metrics.get('completed_tasks', 0)
                total_overdue_tasks += individual_metrics.get('overdue_tasks', 0)
                total_client_contacts += individual_metrics.get('client_contacts', 0)
            
            # Team summary
            report['team_summary'] = {
                'total_case_managers': len(team_members),
                'total_clients': total_clients,
                'total_completed_tasks': total_completed_tasks,
                'total_overdue_tasks': total_overdue_tasks,
                'total_client_contacts': total_client_contacts,
                'avg_clients_per_manager': total_clients / len(team_members) if team_members else 0,
                'task_completion_rate': (total_completed_tasks / (total_completed_tasks + total_overdue_tasks) * 100) if (total_completed_tasks + total_overdue_tasks) > 0 else 0
            }
            
            # Generate trends
            report['trends'] = self._calculate_team_trends(supervisor_id, start_date, end_date)
            
            # Generate recommendations
            report['recommendations'] = self._generate_team_performance_recommendations(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating team performance report: {e}")
            return {'error': str(e)}
    
    def assign_case_manager_to_team(self, supervisor_id: str, case_manager_id: str, team_name: str) -> bool:
        """Assign a case manager to a team"""
        try:
            cursor = self.reminder_db.connection.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO team_assignments 
                (supervisor_id, case_manager_id, team_name, assigned_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                supervisor_id,
                case_manager_id,
                team_name,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            self.reminder_db.connection.commit()
            logger.info(f"Assigned case manager {case_manager_id} to team {team_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning case manager to team: {e}")
            return False
    
    def _get_team_members(self, supervisor_id: str) -> List[Dict[str, Any]]:
        """Get all team members under supervisor"""
        try:
            cursor = self.reminder_db.connection.cursor()
            cursor.execute("""
                SELECT * FROM team_assignments 
                WHERE supervisor_id = ? AND is_active = 1
                ORDER BY team_name, case_manager_id
            """, (supervisor_id,))
            
            team_members = []
            for row in cursor.fetchall():
                member_dict = dict(row)
                member_dict['case_manager_name'] = self._get_case_manager_name(member_dict['case_manager_id'])
                team_members.append(member_dict)
            
            return team_members
            
        except Exception as e:
            logger.error(f"Error getting team members: {e}")
            return []
    
    def _calculate_team_metrics(self, supervisor_id: str, team_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive team metrics"""
        metrics = {
            'total_case_managers': len(team_members),
            'total_clients': 0,
            'total_urgent_items': 0,
            'total_high_priority_items': 0,
            'avg_workload': 0,
            'high_risk_clients': 0,
            'overdue_tasks': 0,
            'completion_rate': 0,
            'response_time': 0,
            'team_utilization': 0
        }
        
        try:
            total_clients = 0
            total_urgent = 0
            total_high_priority = 0
            total_overdue = 0
            total_completed = 0
            high_risk_count = 0
            
            for member in team_members:
                case_manager_id = member['case_manager_id']
                
                # Get daily focus plan
                daily_plan = self.smart_distributor.get_enhanced_daily_focus_plan(case_manager_id)
                
                # Get client insights
                client_insights = daily_plan.get('client_insights', {})
                total_clients += len(client_insights)
                
                # Count high-risk clients
                for client_id, insights in client_insights.items():
                    if insights.get('risk_level') == 'High':
                        high_risk_count += 1
                
                # Get task groups
                task_groups = daily_plan.get('task_groups', {})
                total_urgent += len(task_groups.get('urgent', []))
                total_high_priority += len(task_groups.get('high_priority', []))
                
                # Count overdue tasks
                for task in task_groups.get('urgent', []):
                    if task.get('days_overdue', 0) > 0:
                        total_overdue += 1
                
                # Count completed tasks (mock for now)
                total_completed += len(task_groups.get('scheduled', []))
            
            # Calculate derived metrics
            metrics['total_clients'] = total_clients
            metrics['total_urgent_items'] = total_urgent
            metrics['total_high_priority_items'] = total_high_priority
            metrics['high_risk_clients'] = high_risk_count
            metrics['overdue_tasks'] = total_overdue
            metrics['avg_workload'] = total_clients / len(team_members) if team_members else 0
            metrics['completion_rate'] = (total_completed / (total_completed + total_overdue) * 100) if (total_completed + total_overdue) > 0 else 0
            
            # Calculate team utilization
            if team_members:
                utilization_scores = []
                for member in team_members:
                    case_manager_id = member['case_manager_id']
                    daily_plan = self.smart_distributor.get_enhanced_daily_focus_plan(case_manager_id)
                    time_budget = daily_plan.get('time_budget', {})
                    utilization = time_budget.get('utilization_percentage', 0)
                    utilization_scores.append(utilization)
                
                metrics['team_utilization'] = sum(utilization_scores) / len(utilization_scores)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating team metrics: {e}")
            return metrics
    
    def _get_active_alerts(self, supervisor_id: str) -> List[Dict[str, Any]]:
        """Get active alerts for team"""
        return self.get_team_alerts(supervisor_id)
    
    def _get_performance_insights(self, supervisor_id: str, team_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get performance insights for team"""
        insights = {
            'top_performers': [],
            'needs_attention': [],
            'workload_imbalance': [],
            'efficiency_trends': {}
        }
        
        try:
            performance_data = []
            
            for member in team_members:
                case_manager_id = member['case_manager_id']
                case_manager_name = member['case_manager_name']
                
                # Get performance metrics
                metrics = self._get_case_manager_performance_metrics(case_manager_id)
                
                performance_data.append({
                    'case_manager_id': case_manager_id,
                    'case_manager_name': case_manager_name,
                    'metrics': metrics,
                    'score': self._calculate_performance_score(metrics)
                })
            
            # Sort by performance score
            performance_data.sort(key=lambda x: x['score'], reverse=True)
            
            # Top performers (top 25%)
            top_count = max(1, len(performance_data) // 4)
            insights['top_performers'] = performance_data[:top_count]
            
            # Needs attention (bottom 25%)
            needs_attention_count = max(1, len(performance_data) // 4)
            insights['needs_attention'] = performance_data[-needs_attention_count:]
            
            # Workload imbalance
            avg_workload = sum(p['metrics'].get('total_clients', 0) for p in performance_data) / len(performance_data)
            for performer in performance_data:
                workload = performer['metrics'].get('total_clients', 0)
                if workload > avg_workload * 1.3:  # 30% above average
                    insights['workload_imbalance'].append({
                        'case_manager_name': performer['case_manager_name'],
                        'workload': workload,
                        'avg_workload': avg_workload,
                        'excess_percentage': ((workload - avg_workload) / avg_workload) * 100
                    })
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting performance insights: {e}")
            return insights
    
    def _get_workload_distribution(self, team_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get workload distribution analysis"""
        distribution = {
            'by_case_manager': {},
            'total_clients': 0,
            'avg_clients_per_manager': 0,
            'workload_balance': 'balanced',
            'recommendations': []
        }
        
        try:
            client_counts = []
            
            for member in team_members:
                case_manager_id = member['case_manager_id']
                case_manager_name = member['case_manager_name']
                
                # Get client count
                clients = self.client_integration.get_case_manager_clients(case_manager_id)
                client_count = len(clients)
                client_counts.append(client_count)
                
                # Get workload details
                daily_plan = self.smart_distributor.get_enhanced_daily_focus_plan(case_manager_id)
                time_budget = daily_plan.get('time_budget', {})
                
                distribution['by_case_manager'][case_manager_id] = {
                    'case_manager_name': case_manager_name,
                    'client_count': client_count,
                    'utilization_percentage': time_budget.get('utilization_percentage', 0),
                    'urgent_items': len(daily_plan.get('task_groups', {}).get('urgent', [])),
                    'high_priority_items': len(daily_plan.get('task_groups', {}).get('high_priority', []))
                }
            
            # Calculate distribution metrics
            if client_counts:
                distribution['total_clients'] = sum(client_counts)
                distribution['avg_clients_per_manager'] = sum(client_counts) / len(client_counts)
                
                # Determine workload balance
                max_clients = max(client_counts)
                min_clients = min(client_counts)
                
                if max_clients - min_clients > 5:  # Threshold for imbalance
                    distribution['workload_balance'] = 'imbalanced'
                    distribution['recommendations'].append(
                        f"Consider redistributing clients - range from {min_clients} to {max_clients} clients per manager"
                    )
                elif max_clients > 25:  # High workload threshold
                    distribution['workload_balance'] = 'high'
                    distribution['recommendations'].append(
                        "Some case managers have high workloads - consider additional support"
                    )
            
            return distribution
            
        except Exception as e:
            logger.error(f"Error getting workload distribution: {e}")
            return distribution
    
    def _generate_team_recommendations(self, team_metrics: Dict[str, Any], 
                                     active_alerts: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations for team management"""
        recommendations = []
        
        # High urgent items
        if team_metrics.get('total_urgent_items', 0) > 10:
            recommendations.append("High number of urgent items - consider redistributing workload or providing additional support")
        
        # High risk clients
        if team_metrics.get('high_risk_clients', 0) > 5:
            recommendations.append("Multiple high-risk clients - increase supervision frequency and provide specialized training")
        
        # Low completion rate
        if team_metrics.get('completion_rate', 0) < 70:
            recommendations.append("Low task completion rate - review processes and provide time management training")
        
        # High team utilization
        if team_metrics.get('team_utilization', 0) > 90:
            recommendations.append("Team operating at high capacity - consider hiring additional staff or adjusting caseload sizes")
        
        # Active alerts
        if len(active_alerts) > 5:
            recommendations.append("Multiple active alerts - schedule team meeting to address systemic issues")
        
        return recommendations
    
    def _verify_supervisor_access(self, supervisor_id: str, case_manager_id: str) -> bool:
        """Verify supervisor has access to case manager"""
        try:
            cursor = self.reminder_db.connection.cursor()
            cursor.execute("""
                SELECT id FROM team_assignments 
                WHERE supervisor_id = ? AND case_manager_id = ? AND is_active = 1
            """, (supervisor_id, case_manager_id))
            
            return cursor.fetchone() is not None
            
        except Exception as e:
            logger.error(f"Error verifying supervisor access: {e}")
            return False
    
    def _get_case_manager_performance_metrics(self, case_manager_id: str) -> Dict[str, Any]:
        """Get performance metrics for case manager"""
        metrics = {
            'total_clients': 0,
            'urgent_items': 0,
            'completed_tasks': 0,
            'overdue_tasks': 0,
            'client_contacts': 0,
            'avg_response_time': 0,
            'satisfaction_score': 0
        }
        
        try:
            # Get clients
            clients = self.client_integration.get_case_manager_clients(case_manager_id)
            metrics['total_clients'] = len(clients)
            
            # Get daily plan
            daily_plan = self.smart_distributor.get_enhanced_daily_focus_plan(case_manager_id)
            task_groups = daily_plan.get('task_groups', {})
            
            metrics['urgent_items'] = len(task_groups.get('urgent', []))
            metrics['completed_tasks'] = len(task_groups.get('scheduled', []))  # Mock
            metrics['overdue_tasks'] = len([t for t in task_groups.get('urgent', []) if t.get('days_overdue', 0) > 0])
            
            # Mock additional metrics
            metrics['client_contacts'] = len(clients) * 2  # Assume 2 contacts per client per week
            metrics['avg_response_time'] = 4.5  # hours
            metrics['satisfaction_score'] = 4.2  # out of 5
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting case manager performance metrics: {e}")
            return metrics
    
    def _get_recent_activity(self, case_manager_id: str) -> List[Dict[str, Any]]:
        """Get recent activity for case manager"""
        # Mock recent activity
        return [
            {
                'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
                'activity': 'Contact completed',
                'client_name': 'John Smith',
                'details': 'Weekly check-in call completed'
            },
            {
                'timestamp': (datetime.now() - timedelta(hours=4)).isoformat(),
                'activity': 'Task completed',
                'client_name': 'Maria Garcia',
                'details': 'Housing application submitted'
            }
        ]
    
    def _get_client_risk_distribution(self, clients: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get risk distribution for clients"""
        distribution = {'High': 0, 'Medium': 0, 'Low': 0}
        
        for client in clients:
            risk_level = client.get('calculated_risk_level', 'Medium')
            distribution[risk_level] = distribution.get(risk_level, 0) + 1
        
        return distribution
    
    def _assess_workload(self, daily_plan: Dict[str, Any], clients: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess workload for case manager"""
        time_budget = daily_plan.get('time_budget', {})
        
        return {
            'client_count': len(clients),
            'utilization_percentage': time_budget.get('utilization_percentage', 0),
            'overload_risk': 'High' if time_budget.get('utilization_percentage', 0) > 90 else 'Low',
            'capacity_status': 'Overloaded' if time_budget.get('overload', False) else 'Manageable'
        }
    
    def _generate_case_manager_recommendations(self, performance_metrics: Dict[str, Any], 
                                             daily_plan: Dict[str, Any]) -> List[str]:
        """Generate recommendations for case manager"""
        recommendations = []
        
        # High urgent items
        if performance_metrics.get('urgent_items', 0) > 5:
            recommendations.append("High number of urgent items - prioritize immediate attention")
        
        # High overdue tasks
        if performance_metrics.get('overdue_tasks', 0) > 3:
            recommendations.append("Multiple overdue tasks - review time management and prioritization")
        
        # High workload
        time_budget = daily_plan.get('time_budget', {})
        if time_budget.get('utilization_percentage', 0) > 90:
            recommendations.append("High workload - consider redistributing some clients or tasks")
        
        return recommendations
    
    def _get_case_manager_name(self, case_manager_id: str) -> str:
        """Get case manager name"""
        # Mock implementation
        names = {
            'case_manager_001': 'John Smith',
            'case_manager_002': 'Maria Rodriguez',
            'case_manager_003': 'David Chen',
            'case_manager_004': 'Sarah Johnson'
        }
        return names.get(case_manager_id, case_manager_id)
    
    def _calculate_performance_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall performance score"""
        score = 0
        
        # Client load score (optimal around 15-20 clients)
        client_count = metrics.get('total_clients', 0)
        if 15 <= client_count <= 20:
            score += 25
        elif 10 <= client_count <= 25:
            score += 20
        else:
            score += 10
        
        # Task completion score
        completed = metrics.get('completed_tasks', 0)
        overdue = metrics.get('overdue_tasks', 0)
        if completed + overdue > 0:
            completion_rate = completed / (completed + overdue)
            score += completion_rate * 30
        
        # Urgency management score
        urgent_items = metrics.get('urgent_items', 0)
        if urgent_items <= 2:
            score += 25
        elif urgent_items <= 5:
            score += 15
        else:
            score += 5
        
        # Satisfaction score
        satisfaction = metrics.get('satisfaction_score', 0)
        score += (satisfaction / 5) * 20
        
        return score
    
    def _calculate_performance_rating(self, metrics: Dict[str, Any]) -> str:
        """Calculate performance rating"""
        score = self._calculate_performance_score(metrics)
        
        if score >= 85:
            return 'Excellent'
        elif score >= 70:
            return 'Good'
        elif score >= 55:
            return 'Satisfactory'
        else:
            return 'Needs Improvement'
    
    def _get_performance_metrics_for_period(self, case_manager_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get performance metrics for specific period"""
        # Mock implementation - in production, this would query historical data
        return self._get_case_manager_performance_metrics(case_manager_id)
    
    def _calculate_team_trends(self, supervisor_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Calculate team trends over time"""
        # Mock implementation
        return {
            'client_load_trend': 'increasing',
            'completion_rate_trend': 'stable',
            'urgency_trend': 'improving',
            'satisfaction_trend': 'improving'
        }
    
    def _generate_team_performance_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate team performance recommendations"""
        recommendations = []
        
        team_summary = report.get('team_summary', {})
        
        # Task completion rate
        completion_rate = team_summary.get('task_completion_rate', 0)
        if completion_rate < 80:
            recommendations.append("Team task completion rate below 80% - implement process improvements")
        
        # Average clients per manager
        avg_clients = team_summary.get('avg_clients_per_manager', 0)
        if avg_clients > 22:
            recommendations.append("Average caseload above recommended levels - consider hiring additional staff")
        
        # Individual performance variations
        individual_performance = report.get('individual_performance', {})
        low_performers = [p for p in individual_performance.values() if p['rating'] == 'Needs Improvement']
        
        if len(low_performers) > 0:
            recommendations.append(f"{len(low_performers)} team members need additional support and training")
        
        return recommendations