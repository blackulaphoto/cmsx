"""
Database Integrity API Routes

This module provides API routes for the database integrity manager,
allowing monitoring and maintenance of the 9-database architecture.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from .db_integrity_manager import get_integrity_manager

router = APIRouter(
    prefix="/api/system/integrity",
    tags=["system", "database", "integrity"]
)

@router.get("/status")
async def get_integrity_status():
    """Get the current integrity status of all databases"""
    integrity_manager = get_integrity_manager()
    
    # Run a new check if no previous check exists
    if not integrity_manager.integrity_status:
        integrity_manager.run_integrity_check()
    
    return {
        "status": "success",
        "data": integrity_manager.integrity_status,
        "last_check": integrity_manager.last_check_time.isoformat() if integrity_manager.last_check_time else None
    }

@router.post("/check")
async def run_integrity_check(background_tasks: BackgroundTasks):
    """Run a new integrity check (async in background)"""
    integrity_manager = get_integrity_manager()
    
    # Run check in background
    background_tasks.add_task(integrity_manager.run_integrity_check)
    
    return {
        "status": "success",
        "message": "Integrity check started in background",
        "last_check": integrity_manager.last_check_time.isoformat() if integrity_manager.last_check_time else None
    }

@router.get("/report")
async def get_integrity_report():
    """Get a comprehensive integrity report with recommendations"""
    integrity_manager = get_integrity_manager()
    report = integrity_manager.generate_integrity_report()
    
    return {
        "status": "success",
        "report": report
    }

@router.get("/recommendations")
async def get_repair_recommendations():
    """Get repair recommendations based on integrity check results"""
    integrity_manager = get_integrity_manager()
    
    # Run a new check if no previous check exists
    if not integrity_manager.integrity_status:
        integrity_manager.run_integrity_check()
    
    recommendations = integrity_manager.get_repair_recommendations()
    
    return {
        "status": "success",
        "recommendations": recommendations
    }

@router.post("/repair/sync")
async def repair_client_synchronization(background_tasks: BackgroundTasks):
    """Repair client synchronization issues"""
    integrity_manager = get_integrity_manager()
    
    # Run repair in background
    background_tasks.add_task(integrity_manager.repair_client_synchronization)
    
    return {
        "status": "success",
        "message": "Client synchronization repair started in background"
    }

@router.post("/repair/database/{database}")
async def create_missing_database(database: str):
    """Create a missing database with required tables"""
    integrity_manager = get_integrity_manager()
    
    if database not in integrity_manager.DATABASES:
        raise HTTPException(status_code=400, detail=f"Unknown database: {database}")
    
    result = integrity_manager.create_database(database)
    
    return {
        "status": "success",
        "result": result
    }

@router.post("/repair/table/{database}/{table}")
async def create_missing_table(database: str, table: str):
    """Create a missing table in a database"""
    integrity_manager = get_integrity_manager()
    
    if database not in integrity_manager.DATABASES:
        raise HTTPException(status_code=400, detail=f"Unknown database: {database}")
    
    if database in integrity_manager.REQUIRED_TABLES and table not in integrity_manager.REQUIRED_TABLES[database]:
        raise HTTPException(status_code=400, detail=f"Table {table} is not required for {database}")
    
    result = integrity_manager.create_table(database, table)
    
    return {
        "status": "success",
        "result": result
    }

@router.get("/databases")
async def get_database_status():
    """Get status of all databases"""
    integrity_manager = get_integrity_manager()
    
    # Check database existence
    db_status = integrity_manager.check_database_existence()
    
    return {
        "status": "success",
        "databases": db_status
    }

@router.get("/tables")
async def get_table_status():
    """Get status of all required tables"""
    integrity_manager = get_integrity_manager()
    
    # Check table existence
    table_status = integrity_manager.check_table_existence()
    
    return {
        "status": "success",
        "tables": table_status
    }

@router.get("/sync")
async def get_synchronization_status():
    """Get client synchronization status across databases"""
    integrity_manager = get_integrity_manager()
    
    # Check client synchronization
    sync_status = integrity_manager.check_client_synchronization()
    
    return {
        "status": "success",
        "synchronization": sync_status
    }

@router.get("/permissions")
async def get_permission_status():
    """Verify database access permissions"""
    integrity_manager = get_integrity_manager()
    
    # Check permissions
    perm_status = integrity_manager.verify_permissions()
    
    return {
        "status": "success",
        "permissions": perm_status
    }