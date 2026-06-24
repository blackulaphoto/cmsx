from backend.modules.ai_unified.platform_guide import (
    build_platform_guide_context,
    match_module_for_route,
    select_relevant_modules,
    select_relevant_workflows,
)


def test_match_module_for_nested_admissions_route():
    module = match_module_for_route("/admissions/client-123/forms/intake")
    assert module is not None
    assert module["display_name"] == "Admissions"
    assert module["routes"][0] == "/admissions"


def test_platform_guide_intake_workflow_includes_required_modules():
    context = build_platform_guide_context(
        "I'm about to get a new client, guide me through a full intake in the app.",
        current_route="/smart-dashboard",
        user_role="case_manager",
        is_super_admin=False,
    )
    assert "Current route context: Smart Daily." in context
    assert "Module: Admissions" in context
    assert "Module: Case Management" in context
    assert "Module: Documentation" in context
    assert "Module: Treatment Plan" in context
    assert "Open modules in order: Admissions -> Case Management -> Documentation -> Treatment Plan -> Smart Daily" in context
    assert "/smart-dashboard" not in context
    assert "/case-management" not in context
    assert "/documentation" not in context
    assert "/treatment-plan" not in context


def test_platform_guide_hides_admin_only_modules_for_case_manager():
    context = build_platform_guide_context(
        "Where do I go in the app for a new client intake?",
        current_route="/",
        user_role="case_manager",
        is_super_admin=False,
    )
    assert "Do not present Team Management, Supervisor Dashboard, Owner Cockpit, or Super Admin" in context
    assert "- Supervisor Dashboard" not in context
    assert "- Team Management" not in context
    assert "- Owner Cockpit" not in context


def test_platform_guide_shows_supervisor_for_admin():
    context = build_platform_guide_context(
        "How should I monitor staff workload?",
        current_route="/supervisor-dashboard",
        user_role="admin",
        is_super_admin=False,
    )
    assert "Role context: this user is an admin." in context
    assert "Supervisor Dashboard" in context


def test_ur_question_selects_ur_module_and_workflow():
    modules = select_relevant_modules(
        "How do I use the UR module for authorizations and deadlines?",
        current_route="/case-management",
        user_role="case_manager",
        is_super_admin=False,
    )
    workflows = select_relevant_workflows(
        "How do I use the UR module for authorizations and deadlines?",
        current_route="/case-management",
        user_role="case_manager",
        is_super_admin=False,
    )
    assert any(module["key"] == "ur" for module in modules)
    assert any(workflow["key"] == "ur_workflow" for workflow in workflows)


def test_court_question_returns_legal_documentation_and_smart_daily_context():
    context = build_platform_guide_context(
        "Where do I document a probation and court update?",
        current_route="/legal",
        user_role="case_manager",
        is_super_admin=False,
    )
    assert "Module: Legal" in context
    assert "Module: Documentation" in context
    assert "Module: Smart Daily" in context
    assert "Workflow: Legal, Probation, and Court Update Workflow" in context
    assert "/legal" not in context
    assert "/documentation" not in context
    assert "/smart-dashboard" not in context


def test_housing_question_returns_housing_documentation_and_smart_daily_context():
    context = build_platform_guide_context(
        "How do I coordinate housing follow-up in the app?",
        current_route="/housing",
        user_role="case_manager",
        is_super_admin=False,
    )
    assert "Module: Housing" in context
    assert "Module: Documentation" in context
    assert "Module: Smart Daily" in context


def test_benefits_question_returns_benefits_and_admissions_context():
    context = build_platform_guide_context(
        "Where do I put Medi-Cal info?",
        current_route="/benefits",
        user_role="case_manager",
        is_super_admin=False,
    )
    assert "Module: Benefits" in context
    assert "Module: Admissions" in context


def test_morning_workflow_returns_dashboard_and_smart_daily():
    context = build_platform_guide_context(
        "What should I check every morning?",
        current_route="/",
        user_role="case_manager",
        is_super_admin=False,
    )
    assert "Module: Dashboard" in context
    assert "Module: Smart Daily" in context
    assert "Workflow: Daily Case Manager Morning Workflow" in context
    assert "Open modules in order: Dashboard -> Smart Daily -> Messages -> Case Management" in context
    assert "/smart-dashboard" not in context
    assert "/case-management" not in context


def test_discharge_planning_returns_cross_module_guidance():
    context = build_platform_guide_context(
        "How do I do discharge planning in Ember?",
        current_route="/case-management",
        user_role="case_manager",
        is_super_admin=False,
    )
    assert "Workflow: Discharge Planning" in context
    assert "Case Management -> Documentation -> Treatment Plan -> Housing -> Benefits -> Medical -> Legal -> Jobs -> Smart Daily" in context


def test_unknown_feature_guidance_prefers_closest_available_module_rule():
    context = build_platform_guide_context(
        "Where is the client transportation voucher generator?",
        current_route="/smart-dashboard",
        user_role="case_manager",
        is_super_admin=False,
    )
    assert "The closest available place in Ember is" in context


def test_current_route_changes_selected_module_context():
    benefits_context = build_platform_guide_context(
        "How do I use this app for client coverage work?",
        current_route="/benefits",
        user_role="case_manager",
        is_super_admin=False,
    )
    ur_context = build_platform_guide_context(
        "How do I use this app for client coverage work?",
        current_route="/ur",
        user_role="case_manager",
        is_super_admin=False,
    )
    assert "Current route context: Benefits." in benefits_context
    assert "Current route context: Utilization Review." in ur_context


def test_ur_guidance_hides_raw_routes_by_default():
    context = build_platform_guide_context(
        "How do I use UR?",
        current_route="/ur",
        user_role="case_manager",
        is_super_admin=False,
    )
    assert "Module: Utilization Review" in context
    assert "Module: Documentation" in context
    assert "Module: Smart Daily" in context
    assert "/ur" not in context


def test_explicit_route_question_allows_route_output():
    context = build_platform_guide_context(
        "What is the route for Smart Daily?",
        current_route="/smart-dashboard",
        user_role="case_manager",
        is_super_admin=False,
    )
    assert "Current route context: Smart Daily (/smart-dashboard)." in context
    assert "Smart Daily: /smart-dashboard" in context
    assert "Module: Smart Daily (/smart-dashboard)" in context
