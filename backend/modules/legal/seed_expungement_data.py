#!/usr/bin/env python3
"""
Seed expungement database with sample cases and tasks for UI validation.
"""

from datetime import datetime, timedelta
import json

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from backend.modules.legal.expungement_models import (
    ExpungementCase,
    ExpungementTask,
    ExpungementDatabase
)


def seed_expungement_data():
    db = ExpungementDatabase()

    case_1 = ExpungementCase(
        expungement_id="exp_seed_001",
        client_id="client_seed_001",
        case_number="2018-CR-000789",
        jurisdiction="CA",
        court_name="Los Angeles Superior Court",
        offense_date="2018-02-10",
        conviction_date="2018-05-14",
        offense_type="misdemeanor",
        offense_codes=json.dumps(["PC 484"]),
        eligibility_status="eligible",
        process_stage="document_preparation",
        service_tier="assisted",
        hearing_date=(datetime.now() + timedelta(days=21)).date().isoformat(),
        hearing_time="09:00 AM",
        total_cost=150.0,
        amount_paid=0.0,
        required_documents=json.dumps([
            "petition_form",
            "case_information",
            "proof_of_completion",
            "character_references"
        ]),
        completed_documents=json.dumps([
            "case_information",
            "proof_of_completion"
        ]),
        created_by="seed_script",
        notes="Seeded expungement case for UI validation"
    )

    case_2 = ExpungementCase(
        expungement_id="exp_seed_002",
        client_id="client_seed_002",
        case_number="2020-CR-004321",
        jurisdiction="CA",
        court_name="Van Nuys Courthouse",
        offense_date="2020-06-18",
        conviction_date="2020-10-02",
        offense_type="felony_probation",
        offense_codes=json.dumps(["PC 459"]),
        eligibility_status="conditional",
        process_stage="eligibility_review",
        service_tier="full_service",
        total_cost=1200.0,
        amount_paid=400.0,
        required_documents=json.dumps([
            "petition_form",
            "case_information",
            "probation_completion"
        ]),
        completed_documents=json.dumps([
            "case_information"
        ]),
        created_by="seed_script",
        notes="Seeded expungement case pending probation completion"
    )

    task_1 = ExpungementTask(
        task_id="task_seed_001",
        expungement_id="exp_seed_001",
        client_id="client_seed_001",
        task_type="document_collection",
        task_title="Submit Employment Verification",
        task_description="Obtain verification letters from recent employers",
        priority="urgent",
        status="pending",
        due_date=(datetime.now() + timedelta(days=7)).date().isoformat(),
        assigned_to="client",
        assigned_type="client",
        estimated_hours=2.0,
        created_by="seed_script"
    )

    task_2 = ExpungementTask(
        task_id="task_seed_002",
        expungement_id="exp_seed_002",
        client_id="client_seed_002",
        task_type="probation_review",
        task_title="Verify Probation Completion",
        task_description="Confirm probation completion status with court records",
        priority="high",
        status="in_progress",
        due_date=(datetime.now() + timedelta(days=10)).date().isoformat(),
        assigned_to="case_manager",
        assigned_type="staff",
        estimated_hours=1.5,
        created_by="seed_script"
    )

    task_3 = ExpungementTask(
        task_id="task_seed_003",
        expungement_id="exp_seed_001",
        client_id="client_seed_001",
        task_type="hearing_preparation",
        task_title="Prepare for Court Hearing",
        task_description="Review petition and evidence with client",
        priority="high",
        status="scheduled",
        due_date=(datetime.now() + timedelta(days=14)).date().isoformat(),
        assigned_to="attorney",
        assigned_type="attorney",
        estimated_hours=1.0,
        created_by="seed_script"
    )

    for case in [case_1, case_2]:
        db.save_expungement_case(case)

    for task in [task_1, task_2, task_3]:
        db.save_expungement_task(task)

    print("Seeded expungement cases and tasks.")


if __name__ == "__main__":
    seed_expungement_data()
