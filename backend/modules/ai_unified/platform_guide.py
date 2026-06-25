"""
Popup AI platform guide selector utilities.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .platform_manual import PLATFORM_MANUAL
from .platform_workflows import PLATFORM_WORKFLOWS


QUESTION_PATTERNS = [
    "how do i",
    "walk me through",
    "what steps",
    "where do i",
    "what should i",
    "how should i",
    "how do we",
    "how do you use",
]

ROUTE_REQUEST_PATTERNS = [
    "route",
    "path",
    "url",
    "link",
    "deep link",
    "routing",
    "sidebar route",
    "page route",
]


def match_module_for_route(current_route: Optional[str]) -> Optional[Dict[str, object]]:
    route = (current_route or "").strip()
    if not route:
        return None

    best_match: Optional[Dict[str, object]] = None
    best_len = -1
    for module in PLATFORM_MANUAL:
        for module_route in module["routes"]:
            if ":" in module_route:
                base = module_route.split("/:")[0]
            else:
                base = module_route
            if base == "/":
                if route == "/" and best_len < 1:
                    best_match = module
                    best_len = 1
                continue
            if route == base or route.startswith(f"{base}/"):
                if len(base) > best_len:
                    best_match = module
                    best_len = len(base)
    return best_match


def select_relevant_modules(
    message: str,
    *,
    current_route: Optional[str] = None,
    user_role: Optional[str] = None,
    is_super_admin: bool = False,
    limit: int = 5,
) -> List[Dict[str, object]]:
    text = _normalize(message)
    current_module = match_module_for_route(current_route)
    visible_modules = _visible_modules_for_role(user_role, is_super_admin)
    scored: List[Tuple[int, Dict[str, object]]] = []

    for module in visible_modules:
        score = 0
        if current_module and module["key"] == current_module["key"]:
            score += 10
        for alias in module["aliases"]:
            alias_text = _normalize(str(alias))
            if alias_text and alias_text in text:
                score += 6
        if str(module["display_name"]).lower() in text:
            score += 4
        for route in module["routes"]:
            base = route.split("/:")[0] if ":" in route else route
            if base != "/" and base.lower() in text:
                score += 3
        for example in module["example_questions"]:
            example_text = _normalize(str(example))
            if any(token and token in text for token in example_text.split()[:3]):
                score += 1
        scored.append((score, module))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [module for score, module in scored if score > 0][:limit]

    if not selected and current_module and _is_visible(current_module, user_role, is_super_admin):
        selected.append(current_module)

    if not selected:
        fallback_keys = ["dashboard", "smart_daily", "case_management"]
        for key in fallback_keys:
            module = next((m for m in visible_modules if m["key"] == key), None)
            if module and module not in selected:
                selected.append(module)
        selected = selected[:limit]

    return selected


def select_relevant_workflows(
    message: str,
    *,
    current_route: Optional[str] = None,
    user_role: Optional[str] = None,
    is_super_admin: bool = False,
    limit: int = 3,
) -> List[Dict[str, object]]:
    text = _normalize(message)
    current_module = match_module_for_route(current_route)
    visible_module_keys = {m["key"] for m in _visible_modules_for_role(user_role, is_super_admin)}
    scored: List[Tuple[int, Dict[str, object]]] = []
    asks_for_steps = any(pattern in text for pattern in QUESTION_PATTERNS)

    for workflow in PLATFORM_WORKFLOWS:
        score = 0
        for alias in workflow["aliases"]:
            alias_text = _normalize(str(alias))
            if alias_text and alias_text in text:
                score += 7
        for trigger in workflow["trigger_question_examples"]:
            trigger_text = _normalize(str(trigger))
            if any(term in text for term in trigger_text.split()[:4]):
                score += 1
        if current_module and current_module["key"] in workflow["modules_to_open_in_order"]:
            score += 2
        if asks_for_steps:
            score += 1
        workflow_module_keys = set(workflow["modules_to_open_in_order"])
        if not workflow_module_keys.intersection(visible_module_keys):
            continue
        scored.append((score, workflow))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [workflow for score, workflow in scored if score > 0][:limit]

    if not selected and asks_for_steps:
        fallback = next((w for w in PLATFORM_WORKFLOWS if w["key"] == "daily_case_manager_morning_workflow"), None)
        if fallback:
            selected = [fallback]

    return selected


def build_platform_guide_context(
    message: str,
    *,
    current_route: Optional[str] = None,
    user_role: Optional[str] = None,
    is_super_admin: bool = False,
) -> str:
    expose_routes = _should_expose_routes(message)
    current_module = match_module_for_route(current_route)
    selected_modules = select_relevant_modules(
        message,
        current_route=current_route,
        user_role=user_role,
        is_super_admin=is_super_admin,
    )
    selected_workflows = select_relevant_workflows(
        message,
        current_route=current_route,
        user_role=user_role,
        is_super_admin=is_super_admin,
    )
    visible_modules = _visible_modules_for_role(user_role, is_super_admin)
    visible_by_key = {module["key"]: module for module in visible_modules}
    selected_keys = {module["key"] for module in selected_modules}
    for workflow in selected_workflows:
        for key in workflow["modules_to_open_in_order"]:
            module = visible_by_key.get(key)
            if module and key not in selected_keys:
                selected_modules.append(module)
                selected_keys.add(key)

    lines = [
        "Ember popup assistant manual selector:",
        "Prioritize Ember-specific navigation and data-entry guidance before generic case-management advice.",
        "Routes are internal navigation metadata for matching and route-aware context selection.",
        "In normal user-facing answers, use module names and click or open language instead of raw routes or URLs.",
        "Say things like 'Click Dashboard,' 'Open Smart Daily,' or 'Go to Case Management' instead of showing route paths.",
        "Only expose raw routes when the user explicitly asks for route or path details or is clearly asking about routing behavior.",
        "Do not use 'Route:', 'Action:', or 'Focus:' label blocks unless the user explicitly asks for a formal checklist or table format.",
        "Avoid corporate phrases like 'streamlined process,' 'workflow framework,' or 'paradigm.' Use plain, staff-friendly words.",
        "Write answers in short paragraphs or simple bullet points — not formal numbered multi-section documents.",
        "When giving steps, end with one clear 'Best next step:' sentence naming the single most important action to take right now.",
        "Use module names as action words: 'Click Dashboard,' 'Open Smart Daily,' 'Go to Case Management,' 'Use Documentation,' 'Add a reminder in Smart Daily.'",
        "Explain what data belongs in the module, how it connects to the next module, what should be documented, and what follow-up should go into Smart Daily when applicable.",
        "If live selected-client context is missing, say so plainly and tell the user to select or open the client first.",
        "If a feature seems incomplete or unclear, say 'The closest available place in Ember is ...' and do not invent features.",
        "Do not claim that a note, task, reminder, packet, plan, or record was saved unless a tool or confirmed app action proves it.",
        "Preserve HIPAA-aware and 42 CFR Part 2-aware language. Use documentation template or playbook guidance when the question is about notes.",
    ]

    if current_route:
        if current_module:
            lines.append(_current_route_context_line(current_module, include_route=expose_routes))
        else:
            if expose_routes:
                lines.append(f"Current route context: {current_route}.")
            else:
                lines.append("Current route context: a page is already open in Ember; use that page as the starting point if it matches the question.")

    lines.append(_role_instruction(user_role, is_super_admin))
    lines.append("Short platform index:")
    lines.extend(_platform_index_lines(visible_modules, include_routes=expose_routes))

    lines.append("Selected module manual sections:")
    for module in selected_modules:
        lines.extend(_module_context_lines(module, include_routes=expose_routes))

    if selected_workflows:
        lines.append("Selected workflow recipes:")
        for workflow in selected_workflows:
            lines.extend(_workflow_context_lines(workflow, visible_by_key, include_routes=expose_routes))

    if not selected_workflows:
        lines.append("Workflow guidance: if the user asks for steps, choose the closest workflow from the selected modules and say which part of Ember is the closest available place.")

    return "\n".join(lines)


def _module_context_lines(module: Dict[str, object], *, include_routes: bool) -> List[str]:
    return [
        _module_heading_line(module, include_route=include_routes),
        f"  Purpose: {module['purpose']}",
        f"  Use when: {module['use_when']}",
        f"  Data belongs here: {', '.join(module['required_or_useful_data'])}",
        f"  How to use: {' | '.join(module['step_by_step'])}",
        f"  Related modules: {', '.join(_display_names_for_module_keys(module['related_modules']))}",
        f"  What to document: {module['what_to_document']}",
        f"  Role restrictions: {module['role_restrictions']}",
        f"  Known limitations: {'; '.join(module['known_limitations'])}",
        f"  Example questions: {'; '.join(module['example_questions'])}",
    ]


def _workflow_context_lines(
    workflow: Dict[str, object],
    visible_by_key: Dict[str, Dict[str, object]],
    *,
    include_routes: bool,
) -> List[str]:
    module_order = _display_names_for_workflow(workflow["modules_to_open_in_order"], visible_by_key, include_routes)
    return [
        f"- Workflow: {workflow['display_name']}",
        f"  Trigger examples: {'; '.join(workflow['trigger_question_examples'])}",
        f"  Open modules in order: {' -> '.join(module_order)}",
        f"  Steps: {' | '.join(workflow['step_by_step_actions'])}",
        f"  Data needed: {', '.join(workflow['data_needed'])}",
        f"  Documentation output: {workflow['documentation_output']}",
        f"  Reminders or tasks: {', '.join(workflow['reminders_tasks_to_create'])}",
        f"  Compliance cautions: {'; '.join(workflow['compliance_cautions'])}",
        f"  Incomplete-feature fallback: {workflow['incomplete_or_unclear_fallback']}",
    ]


def _platform_index_lines(visible_modules: List[Dict[str, object]], *, include_routes: bool) -> List[str]:
    index_order = []
    for key in [
        "dashboard",
        "smart_daily",
        "case_management",
        "admissions",
        "documentation",
        "treatment_plan",
        "groups",
        "ur",
        "housing",
        "sober_living",
        "sober_living_directory",
        "benefits",
        "medical",
        "legal",
        "fmla",
        "messages",
        "resume",
        "jobs",
        "team_management",
        "supervisor_dashboard",
        "owner_cockpit",
        "super_admin",
        "settings",
        "profile",
        "support",
        "billing",
        "system_integrity",
        "integration_audit",
    ]:
        module = next((m for m in visible_modules if m["key"] == key), None)
        if module:
            if include_routes:
                index_order.append(f"- {module['display_name']}: {module['routes'][0]}")
            else:
                index_order.append(f"- {module['display_name']}")
    return index_order


def _visible_modules_for_role(user_role: Optional[str], is_super_admin: bool) -> List[Dict[str, object]]:
    visible = []
    for module in PLATFORM_MANUAL:
        if _is_visible(module, user_role, is_super_admin):
            visible.append(module)
    return visible


def _is_visible(module: Dict[str, object], user_role: Optional[str], is_super_admin: bool) -> bool:
    restriction = str(module["role_restrictions"]).lower()
    is_admin = (user_role or "").strip().lower() == "admin"
    if "super-admin only" in restriction:
        return is_super_admin
    if "admin only" in restriction:
        return is_admin
    return True


def _role_instruction(user_role: Optional[str], is_super_admin: bool) -> str:
    is_admin = (user_role or "").strip().lower() == "admin"
    if is_super_admin:
        return "Role context: this user is a super-admin. Owner Cockpit and Super Admin are available only for platform operations, not normal client workflow."
    if is_admin:
        return "Role context: this user is an admin. Supervisor Dashboard and Team Management may be available; Owner Cockpit and Super Admin remain restricted."
    return "Role context: user is a non-admin case-management user. Do not present Team Management, Supervisor Dashboard, Owner Cockpit, or Super Admin as available workflow steps."


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _should_expose_routes(message: str) -> bool:
    text = _normalize(message)
    if any(pattern in text for pattern in ROUTE_REQUEST_PATTERNS):
        return True
    return "/" in (message or "")


def _current_route_context_line(module: Dict[str, object], *, include_route: bool) -> str:
    if include_route:
        return f"Current route context: {module['display_name']} ({module['routes'][0]})."
    return f"Current route context: {module['display_name']}."


def _module_heading_line(module: Dict[str, object], *, include_route: bool) -> str:
    if include_route:
        return f"- Module: {module['display_name']} ({module['routes'][0]})"
    return f"- Module: {module['display_name']}"


def _display_names_for_module_keys(module_keys: List[str]) -> List[str]:
    names = []
    for key in module_keys:
        module = next((entry for entry in PLATFORM_MANUAL if entry["key"] == key), None)
        names.append(str(module["display_name"]) if module else str(key))
    return names


def _display_names_for_workflow(
    module_keys: List[str],
    visible_by_key: Dict[str, Dict[str, object]],
    include_routes: bool,
) -> List[str]:
    names = []
    for key in module_keys:
        module = visible_by_key.get(key)
        if module:
            if include_routes:
                names.append(f"{module['display_name']} ({module['routes'][0]})")
            else:
                names.append(str(module["display_name"]))
        else:
            names.append(str(key))
    return names
