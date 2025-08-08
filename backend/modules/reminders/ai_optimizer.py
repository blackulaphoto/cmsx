#!/usr/bin/env python3
"""
Automated Progress Tracking and AI-Powered Workload Optimization
Machine learning-based optimization for case management workflows
"""

import logging
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error
import joblib
import os

from .database_integration import SmartTaskDistributorIntegrated
from .notifications import NotificationService
from .models import ReminderDatabase

logger = logging.getLogger(__name__)

class ProgressTracker:
    """
    Automated progress tracking system that monitors task completion,
    client progress, and system performance
    """
    
    def __init__(self, smart_distributor: SmartTaskDistributorIntegrated):
        self.smart_distributor = smart_distributor
        self.reminder_db = smart_distributor.reminder_db
        self.client_integration = smart_distributor.client_integration
        
        # Create progress tracking tables
        self._create_progress_tables()
    
    def _create_progress_tables(self):
        """Create progress tracking database tables"""
        if not self.reminder_db.connection:
            self.reminder_db.connect()
        
        progress_tables = [
            """
            CREATE TABLE IF NOT EXISTS task_completions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                completion_id TEXT UNIQUE NOT NULL,
                case_manager_id TEXT NOT NULL,
                client_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                estimated_minutes INTEGER,
                actual_minutes INTEGER,
                completion_date TEXT NOT NULL,
                completion_quality TEXT,
                outcome TEXT,
                notes TEXT,
                created_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS client_progress_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                case_manager_id TEXT NOT NULL,
                snapshot_date TEXT NOT NULL,
                housing_stability_score INTEGER,
                employment_progress_score INTEGER,
                service_engagement_score INTEGER,
                program_compliance_score INTEGER,
                overall_progress_score INTEGER,
                risk_level TEXT,
                key_milestones TEXT,
                barriers_identified TEXT,
                interventions_applied TEXT,
                created_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS case_manager_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                performance_id TEXT UNIQUE NOT NULL,
                case_manager_id TEXT NOT NULL,
                measurement_date TEXT NOT NULL,
                total_clients INTEGER,
                tasks_completed INTEGER,
                tasks_overdue INTEGER,
                avg_task_completion_time REAL,
                client_satisfaction_avg REAL,
                workload_utilization REAL,
                efficiency_score REAL,
                quality_score REAL,
                created_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_id TEXT UNIQUE NOT NULL,
                metric_date TEXT NOT NULL,
                total_active_clients INTEGER,
                total_case_managers INTEGER,
                avg_caseload_size REAL,
                system_utilization REAL,
                alert_resolution_time REAL,
                client_outcome_success_rate REAL,
                process_efficiency_score REAL,
                created_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS predictive_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_id TEXT UNIQUE NOT NULL,
                case_manager_id TEXT,
                client_id TEXT,
                prediction_type TEXT NOT NULL,
                prediction_value REAL,
                confidence_score REAL,
                predicted_date TEXT,
                actual_outcome REAL,
                model_version TEXT,
                created_at TEXT
            )
            """
        ]
        
        try:
            for table_sql in progress_tables:
                self.reminder_db.connection.execute(table_sql)
            self.reminder_db.connection.commit()
            logger.info("Progress tracking tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create progress tracking tables: {e}")
    
    def record_task_completion(self, case_manager_id: str, client_id: str, task_id: str,
                             task_type: str, estimated_minutes: int, actual_minutes: int,
                             completion_quality: str, outcome: str, notes: str = "") -> bool:
        """Record task completion with performance metrics"""
        try:
            cursor = self.reminder_db.connection.cursor()
            cursor.execute("""
                INSERT INTO task_completions
                (completion_id, case_manager_id, client_id, task_id, task_type,
                 estimated_minutes, actual_minutes, completion_date, completion_quality,
                 outcome, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"comp_{datetime.now().timestamp()}",
                case_manager_id,
                client_id,
                task_id,
                task_type,
                estimated_minutes,
                actual_minutes,
                datetime.now().isoformat(),
                completion_quality,
                outcome,
                notes,
                datetime.now().isoformat()
            ))
            
            self.reminder_db.connection.commit()
            
            # Update client progress
            self._update_client_progress(client_id, case_manager_id, task_type, outcome)
            
            # Update case manager performance
            self._update_case_manager_performance(case_manager_id)
            
            logger.info(f"Task completion recorded: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording task completion: {e}")
            return False
    
    def create_client_progress_snapshot(self, client_id: str, case_manager_id: str) -> bool:
        """Create a progress snapshot for a client"""
        try:
            # Get current progress metrics
            progress_metrics = self.client_integration.get_client_progress_metrics(client_id)
            
            cursor = self.reminder_db.connection.cursor()
            cursor.execute("""
                INSERT INTO client_progress_snapshots
                (snapshot_id, client_id, case_manager_id, snapshot_date,
                 housing_stability_score, employment_progress_score, service_engagement_score,
                 program_compliance_score, overall_progress_score, risk_level,
                 key_milestones, barriers_identified, interventions_applied, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"snap_{datetime.now().timestamp()}",
                client_id,
                case_manager_id,
                datetime.now().isoformat(),
                progress_metrics.get('housing_stability', 0),
                progress_metrics.get('employment_progress', 0),
                progress_metrics.get('service_engagement', 0),
                progress_metrics.get('program_compliance', 0),
                progress_metrics.get('overall_progress', 0),
                'Medium',  # Mock risk level
                json.dumps(progress_metrics.get('key_milestones', [])),
                json.dumps(progress_metrics.get('barriers_identified', [])),
                json.dumps([]),  # Interventions applied
                datetime.now().isoformat()
            ))
            
            self.reminder_db.connection.commit()
            logger.info(f"Client progress snapshot created: {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating client progress snapshot: {e}")
            return False
    
    def get_progress_trends(self, client_id: str, days: int = 30) -> Dict[str, Any]:
        """Get progress trends for a client"""
        try:
            cursor = self.reminder_db.connection.cursor()
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute("""
                SELECT * FROM client_progress_snapshots
                WHERE client_id = ? AND snapshot_date >= ?
                ORDER BY snapshot_date ASC
            """, (client_id, start_date))
            
            snapshots = [dict(row) for row in cursor.fetchall()]
            
            if len(snapshots) < 2:
                return {'error': 'Insufficient data for trend analysis'}
            
            # Calculate trends
            trends = {
                'housing_stability': self._calculate_trend([s['housing_stability_score'] for s in snapshots]),
                'employment_progress': self._calculate_trend([s['employment_progress_score'] for s in snapshots]),
                'service_engagement': self._calculate_trend([s['service_engagement_score'] for s in snapshots]),
                'program_compliance': self._calculate_trend([s['program_compliance_score'] for s in snapshots]),
                'overall_progress': self._calculate_trend([s['overall_progress_score'] for s in snapshots])
            }
            
            return {
                'client_id': client_id,
                'period_days': days,
                'snapshots_count': len(snapshots),
                'trends': trends,
                'latest_snapshot': snapshots[-1] if snapshots else None
            }
            
        except Exception as e:
            logger.error(f"Error getting progress trends: {e}")
            return {'error': str(e)}
    
    def _update_client_progress(self, client_id: str, case_manager_id: str, task_type: str, outcome: str):
        """Update client progress based on task completion"""
        try:
            # Create progress snapshot
            self.create_client_progress_snapshot(client_id, case_manager_id)
            
            # Update program status if needed
            status_updates = {}
            
            if task_type == 'housing_search' and outcome == 'Successful':
                status_updates['housing_status'] = 'Secured'
            elif task_type == 'employment_prep' and outcome == 'Successful':
                status_updates['employment_status'] = 'Job Ready'
            
            if status_updates:
                status_updates['last_updated'] = datetime.now().isoformat()
                self.client_integration.update_client_program_status(client_id, status_updates)
                logger.info(f"Updated client program status: {client_id}")
            
        except Exception as e:
            logger.error(f"Error updating client progress: {e}")
    
    def _update_case_manager_performance(self, case_manager_id: str):
        """Update case manager performance metrics"""
        try:
            # Get recent task completions
            cursor = self.reminder_db.connection.cursor()
            cursor.execute("""
                SELECT * FROM task_completions
                WHERE case_manager_id = ? AND completion_date >= ?
                ORDER BY completion_date DESC
                LIMIT 100
            """, (case_manager_id, (datetime.now() - timedelta(days=7)).isoformat()))
            
            completions = [dict(row) for row in cursor.fetchall()]
            
            if not completions:
                return
            
            # Calculate performance metrics
            total_tasks = len(completions)
            avg_completion_time = sum(c['actual_minutes'] for c in completions) / total_tasks
            quality_scores = [self._map_quality_to_score(c['completion_quality']) for c in completions]
            avg_quality = sum(quality_scores) / len(quality_scores)
            
            # Get current clients
            clients = self.client_integration.get_case_manager_clients(case_manager_id)
            
            # Calculate efficiency score
            efficiency_score = self._calculate_efficiency_score(completions, clients)
            
            # Store performance metrics
            cursor.execute("""
                INSERT INTO case_manager_performance
                (performance_id, case_manager_id, measurement_date, total_clients,
                 tasks_completed, avg_task_completion_time, workload_utilization,
                 efficiency_score, quality_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"perf_{datetime.now().timestamp()}",
                case_manager_id,
                datetime.now().isoformat(),
                len(clients),
                total_tasks,
                avg_completion_time,
                75.0,  # Mock utilization
                efficiency_score,
                avg_quality,
                datetime.now().isoformat()
            ))
            
            self.reminder_db.connection.commit()
            logger.info(f"Case manager performance updated: {case_manager_id}")
            
        except Exception as e:
            logger.error(f"Error updating case manager performance: {e}")
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend direction and magnitude"""
        if len(values) < 2:
            return {'direction': 'stable', 'magnitude': 0, 'confidence': 0}
        
        # Simple linear regression
        x = np.arange(len(values))
        y = np.array(values)
        
        slope = np.polyfit(x, y, 1)[0]
        
        # Determine direction
        if slope > 1:
            direction = 'improving'
        elif slope < -1:
            direction = 'declining'
        else:
            direction = 'stable'
        
        # Calculate confidence (R-squared)
        correlation = np.corrcoef(x, y)[0, 1] ** 2
        
        return {
            'direction': direction,
            'magnitude': abs(slope),
            'confidence': correlation,
            'latest_value': values[-1],
            'change_from_start': values[-1] - values[0]
        }
    
    def _map_quality_to_score(self, quality: str) -> float:
        """Map quality rating to numeric score"""
        quality_map = {
            'Excellent': 5.0,
            'Good': 4.0,
            'Satisfactory': 3.0,
            'Poor': 2.0,
            'Unacceptable': 1.0
        }
        return quality_map.get(quality, 3.0)
    
    def _calculate_efficiency_score(self, completions: List[Dict], clients: List[Dict]) -> float:
        """Calculate efficiency score for case manager"""
        if not completions:
            return 0.0
        
        # Base efficiency on time accuracy
        time_accuracy = []
        for completion in completions:
            estimated = completion.get('estimated_minutes', 30)
            actual = completion.get('actual_minutes', 30)
            if estimated > 0:
                accuracy = 1.0 - abs(actual - estimated) / estimated
                time_accuracy.append(max(0, accuracy))
        
        base_efficiency = sum(time_accuracy) / len(time_accuracy) if time_accuracy else 0.5
        
        # Adjust for caseload size
        caseload_factor = min(1.0, 20 / len(clients)) if clients else 1.0
        
        return base_efficiency * caseload_factor * 100

class AIWorkloadOptimizer:
    """
    AI-powered workload optimization system using machine learning
    to predict workload, optimize task distribution, and recommend improvements
    """
    
    def __init__(self, progress_tracker: ProgressTracker):
        self.progress_tracker = progress_tracker
        self.reminder_db = progress_tracker.reminder_db
        self.client_integration = progress_tracker.client_integration
        
        # ML models
        self.workload_predictor = None
        self.task_duration_predictor = None
        self.client_success_predictor = None
        self.scaler = StandardScaler()
        
        # Model file paths
        self.model_dir = '/app/models/'
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Initialize or load models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize or load existing ML models"""
        try:
            # Try to load existing models
            self._load_models()
            logger.info("Loaded existing ML models")
        except:
            # Create new models
            self._create_new_models()
            logger.info("Created new ML models")
    
    def _create_new_models(self):
        """Create new ML models"""
        # Workload predictor - predicts case manager workload capacity
        self.workload_predictor = RandomForestRegressor(
            n_estimators=100,
            random_state=42,
            max_depth=10
        )
        
        # Task duration predictor - predicts how long tasks will take
        self.task_duration_predictor = RandomForestRegressor(
            n_estimators=100,
            random_state=42,
            max_depth=8
        )
        
        # Client success predictor - predicts client success probability
        self.client_success_predictor = RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            max_depth=12
        )
        
        logger.info("Created new ML models")
    
    def _load_models(self):
        """Load existing ML models"""
        self.workload_predictor = joblib.load(f'{self.model_dir}/workload_predictor.pkl')
        self.task_duration_predictor = joblib.load(f'{self.model_dir}/task_duration_predictor.pkl')
        self.client_success_predictor = joblib.load(f'{self.model_dir}/client_success_predictor.pkl')
        self.scaler = joblib.load(f'{self.model_dir}/scaler.pkl')
    
    def _save_models(self):
        """Save ML models to disk"""
        joblib.dump(self.workload_predictor, f'{self.model_dir}/workload_predictor.pkl')
        joblib.dump(self.task_duration_predictor, f'{self.model_dir}/task_duration_predictor.pkl')
        joblib.dump(self.client_success_predictor, f'{self.model_dir}/client_success_predictor.pkl')
        joblib.dump(self.scaler, f'{self.model_dir}/scaler.pkl')
    
    def train_models(self) -> Dict[str, Any]:
        """Train all ML models with historical data"""
        try:
            # Get training data
            training_data = self._prepare_training_data()
            
            if not training_data:
                return {'error': 'Insufficient training data'}
            
            results = {}
            
            # Train workload predictor
            if len(training_data['workload_data']) > 10:
                results['workload_model'] = self._train_workload_predictor(training_data['workload_data'])
            
            # Train task duration predictor
            if len(training_data['task_data']) > 10:
                results['task_duration_model'] = self._train_task_duration_predictor(training_data['task_data'])
            
            # Train client success predictor
            if len(training_data['client_data']) > 10:
                results['client_success_model'] = self._train_client_success_predictor(training_data['client_data'])
            
            # Save models
            self._save_models()
            
            return results
            
        except Exception as e:
            logger.error(f"Error training models: {e}")
            return {'error': str(e)}
    
    def predict_optimal_workload(self, case_manager_id: str) -> Dict[str, Any]:
        """Predict optimal workload for case manager"""
        try:
            # Get case manager features
            features = self._get_case_manager_features(case_manager_id)
            
            if not features:
                return {'error': 'Insufficient data for prediction'}
            
            # Prepare features for prediction
            feature_array = np.array([features]).reshape(1, -1)
            
            # Predict optimal workload
            if self.workload_predictor:
                predicted_workload = self.workload_predictor.predict(feature_array)[0]
                
                # Get current workload
                current_clients = self.client_integration.get_case_manager_clients(case_manager_id)
                current_workload = len(current_clients)
                
                return {
                    'case_manager_id': case_manager_id,
                    'current_workload': current_workload,
                    'predicted_optimal': predicted_workload,
                    'recommendation': self._generate_workload_recommendation(current_workload, predicted_workload),
                    'confidence': 0.85  # Mock confidence score
                }
            
            return {'error': 'Workload prediction model not available'}
            
        except Exception as e:
            logger.error(f"Error predicting optimal workload: {e}")
            return {'error': str(e)}
    
    def predict_task_duration(self, task_type: str, client_id: str, case_manager_id: str) -> Dict[str, Any]:
        """Predict how long a task will take"""
        try:
            # Get task features
            features = self._get_task_features(task_type, client_id, case_manager_id)
            
            if not features:
                return {'error': 'Insufficient data for prediction'}
            
            # Prepare features for prediction
            feature_array = np.array([features]).reshape(1, -1)
            
            # Predict duration
            if self.task_duration_predictor:
                predicted_duration = self.task_duration_predictor.predict(feature_array)[0]
                
                return {
                    'task_type': task_type,
                    'client_id': client_id,
                    'case_manager_id': case_manager_id,
                    'predicted_duration_minutes': int(predicted_duration),
                    'confidence': 0.78  # Mock confidence score
                }
            
            return {'error': 'Task duration prediction model not available'}
            
        except Exception as e:
            logger.error(f"Error predicting task duration: {e}")
            return {'error': str(e)}
    
    def predict_client_success(self, client_id: str) -> Dict[str, Any]:
        """Predict client success probability"""
        try:
            # Get client features
            features = self._get_client_features(client_id)
            
            if not features:
                return {'error': 'Insufficient data for prediction'}
            
            # Prepare features for prediction
            feature_array = np.array([features]).reshape(1, -1)
            
            # Predict success probability
            if self.client_success_predictor:
                success_probability = self.client_success_predictor.predict_proba(feature_array)[0][1]
                
                # Get risk factors
                risk_factors = self._identify_risk_factors(client_id, features)
                
                return {
                    'client_id': client_id,
                    'success_probability': success_probability,
                    'risk_level': 'High' if success_probability < 0.6 else 'Medium' if success_probability < 0.8 else 'Low',
                    'risk_factors': risk_factors,
                    'recommendations': self._generate_client_recommendations(success_probability, risk_factors)
                }
            
            return {'error': 'Client success prediction model not available'}
            
        except Exception as e:
            logger.error(f"Error predicting client success: {e}")
            return {'error': str(e)}
    
    def optimize_daily_schedule(self, case_manager_id: str, date: str = None) -> Dict[str, Any]:
        """Optimize daily schedule using AI predictions"""
        try:
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            
            # Get current daily plan
            daily_plan = self.progress_tracker.smart_distributor.get_enhanced_daily_focus_plan(case_manager_id, date)
            
            # Optimize task ordering
            optimized_tasks = self._optimize_task_order(daily_plan.get('task_groups', {}))
            
            # Predict total workload
            workload_prediction = self.predict_optimal_workload(case_manager_id)
            
            # Generate optimization recommendations
            recommendations = self._generate_optimization_recommendations(
                optimized_tasks, workload_prediction, daily_plan
            )
            
            return {
                'case_manager_id': case_manager_id,
                'date': date,
                'optimized_tasks': optimized_tasks,
                'workload_prediction': workload_prediction,
                'recommendations': recommendations,
                'estimated_total_time': self._calculate_total_time(optimized_tasks)
            }
            
        except Exception as e:
            logger.error(f"Error optimizing daily schedule: {e}")
            return {'error': str(e)}
    
    def _prepare_training_data(self) -> Dict[str, Any]:
        """Prepare training data for ML models"""
        try:
            cursor = self.reminder_db.connection.cursor()
            
            # Get workload data
            cursor.execute("""
                SELECT * FROM case_manager_performance
                WHERE measurement_date >= ?
            """, ((datetime.now() - timedelta(days=90)).isoformat(),))
            workload_data = [dict(row) for row in cursor.fetchall()]
            
            # Get task completion data
            cursor.execute("""
                SELECT * FROM task_completions
                WHERE completion_date >= ?
            """, ((datetime.now() - timedelta(days=90)).isoformat(),))
            task_data = [dict(row) for row in cursor.fetchall()]
            
            # Get client progress data
            cursor.execute("""
                SELECT * FROM client_progress_snapshots
                WHERE snapshot_date >= ?
            """, ((datetime.now() - timedelta(days=90)).isoformat(),))
            client_data = [dict(row) for row in cursor.fetchall()]
            
            return {
                'workload_data': workload_data,
                'task_data': task_data,
                'client_data': client_data
            }
            
        except Exception as e:
            logger.error(f"Error preparing training data: {e}")
            return {}
    
    def _train_workload_predictor(self, workload_data: List[Dict]) -> Dict[str, Any]:
        """Train workload prediction model"""
        try:
            # Prepare features and targets
            features = []
            targets = []
            
            for record in workload_data:
                feature_vector = [
                    record.get('total_clients', 0),
                    record.get('tasks_completed', 0),
                    record.get('avg_task_completion_time', 30),
                    record.get('workload_utilization', 50),
                    record.get('efficiency_score', 50)
                ]
                features.append(feature_vector)
                targets.append(record.get('total_clients', 0))
            
            X = np.array(features)
            y = np.array(targets)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.workload_predictor.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.workload_predictor.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            
            return {
                'model_type': 'workload_predictor',
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'mse': mse,
                'feature_importance': self.workload_predictor.feature_importances_.tolist()
            }
            
        except Exception as e:
            logger.error(f"Error training workload predictor: {e}")
            return {'error': str(e)}
    
    def _train_task_duration_predictor(self, task_data: List[Dict]) -> Dict[str, Any]:
        """Train task duration prediction model"""
        try:
            # Prepare features and targets
            features = []
            targets = []
            
            task_type_map = {'phone_call': 1, 'appointment': 2, 'paperwork': 3, 'follow_up': 4}
            
            for record in task_data:
                feature_vector = [
                    task_type_map.get(record.get('task_type', ''), 1),
                    record.get('estimated_minutes', 30),
                    1 if record.get('completion_quality', '') == 'Excellent' else 0,
                    len(record.get('notes', ''))
                ]
                features.append(feature_vector)
                targets.append(record.get('actual_minutes', 30))
            
            X = np.array(features)
            y = np.array(targets)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Train model
            self.task_duration_predictor.fit(X_train, y_train)
            
            # Evaluate
            y_pred = self.task_duration_predictor.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            
            return {
                'model_type': 'task_duration_predictor',
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'mse': mse,
                'feature_importance': self.task_duration_predictor.feature_importances_.tolist()
            }
            
        except Exception as e:
            logger.error(f"Error training task duration predictor: {e}")
            return {'error': str(e)}
    
    def _train_client_success_predictor(self, client_data: List[Dict]) -> Dict[str, Any]:
        """Train client success prediction model"""
        try:
            # Prepare features and targets
            features = []
            targets = []
            
            for record in client_data:
                feature_vector = [
                    record.get('housing_stability_score', 0),
                    record.get('employment_progress_score', 0),
                    record.get('service_engagement_score', 0),
                    record.get('program_compliance_score', 0),
                    1 if record.get('risk_level', '') == 'High' else 0
                ]
                features.append(feature_vector)
                # Success defined as overall progress > 70
                targets.append(1 if record.get('overall_progress_score', 0) > 70 else 0)
            
            X = np.array(features)
            y = np.array(targets)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Train model
            self.client_success_predictor.fit(X_train, y_train)
            
            # Evaluate
            y_pred = self.client_success_predictor.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            return {
                'model_type': 'client_success_predictor',
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'accuracy': accuracy,
                'feature_importance': self.client_success_predictor.feature_importances_.tolist()
            }
            
        except Exception as e:
            logger.error(f"Error training client success predictor: {e}")
            return {'error': str(e)}
    
    def _get_case_manager_features(self, case_manager_id: str) -> List[float]:
        """Get features for case manager workload prediction"""
        try:
            # Get recent performance data
            cursor = self.reminder_db.connection.cursor()
            cursor.execute("""
                SELECT * FROM case_manager_performance
                WHERE case_manager_id = ?
                ORDER BY measurement_date DESC
                LIMIT 1
            """, (case_manager_id,))
            
            performance = cursor.fetchone()
            if performance:
                performance = dict(performance)
                return [
                    performance.get('total_clients', 0),
                    performance.get('tasks_completed', 0),
                    performance.get('avg_task_completion_time', 30),
                    performance.get('workload_utilization', 50),
                    performance.get('efficiency_score', 50)
                ]
            
            return [15, 10, 30, 75, 65]  # Default values
            
        except Exception as e:
            logger.error(f"Error getting case manager features: {e}")
            return []
    
    def _get_task_features(self, task_type: str, client_id: str, case_manager_id: str) -> List[float]:
        """Get features for task duration prediction"""
        try:
            task_type_map = {'phone_call': 1, 'appointment': 2, 'paperwork': 3, 'follow_up': 4}
            
            # Get client complexity (mock)
            client_complexity = 2  # 1-3 scale
            
            # Get case manager efficiency
            efficiency = 65  # Mock efficiency score
            
            return [
                task_type_map.get(task_type, 1),
                30,  # Estimated minutes
                client_complexity,
                efficiency
            ]
            
        except Exception as e:
            logger.error(f"Error getting task features: {e}")
            return []
    
    def _get_client_features(self, client_id: str) -> List[float]:
        """Get features for client success prediction"""
        try:
            # Get latest progress snapshot
            cursor = self.reminder_db.connection.cursor()
            cursor.execute("""
                SELECT * FROM client_progress_snapshots
                WHERE client_id = ?
                ORDER BY snapshot_date DESC
                LIMIT 1
            """, (client_id,))
            
            snapshot = cursor.fetchone()
            if snapshot:
                snapshot = dict(snapshot)
                return [
                    snapshot.get('housing_stability_score', 0),
                    snapshot.get('employment_progress_score', 0),
                    snapshot.get('service_engagement_score', 0),
                    snapshot.get('program_compliance_score', 0),
                    1 if snapshot.get('risk_level', '') == 'High' else 0
                ]
            
            return [50, 40, 60, 70, 0]  # Default values
            
        except Exception as e:
            logger.error(f"Error getting client features: {e}")
            return []
    
    def _generate_workload_recommendation(self, current: int, optimal: int) -> str:
        """Generate workload recommendation"""
        diff = current - optimal
        
        if diff > 5:
            return f"Current workload ({current}) is {diff} clients above optimal ({optimal}). Consider redistributing clients."
        elif diff < -3:
            return f"Current workload ({current}) is {abs(diff)} clients below optimal ({optimal}). Can handle more clients."
        else:
            return f"Current workload ({current}) is near optimal ({optimal}). Good balance."
    
    def _identify_risk_factors(self, client_id: str, features: List[float]) -> List[str]:
        """Identify risk factors for client"""
        risk_factors = []
        
        if len(features) >= 5:
            if features[0] < 40:  # Housing stability
                risk_factors.append("Low housing stability")
            if features[1] < 30:  # Employment progress
                risk_factors.append("Limited employment progress")
            if features[2] < 50:  # Service engagement
                risk_factors.append("Low service engagement")
            if features[3] < 60:  # Program compliance
                risk_factors.append("Program compliance issues")
            if features[4] == 1:  # High risk
                risk_factors.append("High risk classification")
        
        return risk_factors
    
    def _generate_client_recommendations(self, success_probability: float, risk_factors: List[str]) -> List[str]:
        """Generate client recommendations"""
        recommendations = []
        
        if success_probability < 0.6:
            recommendations.append("High risk of program failure - increase intervention intensity")
        
        if "Low housing stability" in risk_factors:
            recommendations.append("Prioritize housing search and stability interventions")
        
        if "Limited employment progress" in risk_factors:
            recommendations.append("Focus on employment readiness and job search activities")
        
        if "Low service engagement" in risk_factors:
            recommendations.append("Increase motivation and engagement strategies")
        
        if "Program compliance issues" in risk_factors:
            recommendations.append("Address barriers to program participation")
        
        return recommendations
    
    def _optimize_task_order(self, task_groups: Dict[str, List]) -> Dict[str, List]:
        """Optimize task ordering for maximum efficiency"""
        optimized = {}
        
        for group_name, tasks in task_groups.items():
            # Sort tasks by predicted efficiency
            sorted_tasks = sorted(tasks, key=lambda t: self._calculate_task_priority(t), reverse=True)
            optimized[group_name] = sorted_tasks
        
        return optimized
    
    def _calculate_task_priority(self, task: Dict[str, Any]) -> float:
        """Calculate task priority for optimization"""
        priority_score = 0
        
        # Urgency score
        priority_score += task.get('urgency_score', 0) * 0.4
        
        # Predicted duration (shorter tasks get higher priority)
        predicted_duration = task.get('estimated_minutes', 30)
        priority_score += (60 - predicted_duration) * 0.3
        
        # Client success probability
        client_id = task.get('client_id', '')
        if client_id:
            success_prediction = self.predict_client_success(client_id)
            if 'success_probability' in success_prediction:
                priority_score += success_prediction['success_probability'] * 0.3
        
        return priority_score
    
    def _generate_optimization_recommendations(self, optimized_tasks: Dict, workload_prediction: Dict, daily_plan: Dict) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Workload recommendations
        if 'recommendation' in workload_prediction:
            recommendations.append(workload_prediction['recommendation'])
        
        # Task distribution recommendations
        total_urgent = len(optimized_tasks.get('urgent', []))
        if total_urgent > 5:
            recommendations.append("High number of urgent tasks - consider delegating or rescheduling non-critical items")
        
        # Time management recommendations
        time_budget = daily_plan.get('time_budget', {})
        if time_budget.get('utilization_percentage', 0) > 90:
            recommendations.append("Schedule at capacity - build in buffer time for unexpected issues")
        
        return recommendations
    
    def _calculate_total_time(self, optimized_tasks: Dict) -> int:
        """Calculate total estimated time for all tasks"""
        total_time = 0
        
        for group_name, tasks in optimized_tasks.items():
            for task in tasks:
                total_time += task.get('estimated_minutes', 30)
        
        return total_time