# Popup AI Platform Guide

This note explains where the popup AI platform-manual logic lives and how it is selected.

## Files

- Human-readable manual: `docs/platform/EMBER_USER_MANUAL.md`
- Structured module manual: `backend/modules/ai_unified/platform_manual.py`
- Structured workflow recipes: `backend/modules/ai_unified/platform_workflows.py`
- Selector and prompt-context builder: `backend/modules/ai_unified/platform_guide.py`
- Popup route injection: `backend/modules/ai_unified/unified_routes.py`

## How selection works

The popup assistant does not receive the full manual on every request.

The selector currently does three things:

1. Builds a short platform index for the visible modules.
2. Adds current-route context when `current_route` is supplied by the popup.
3. Selects only the most relevant manual sections and workflow recipes based on:
   - user-message keywords
   - module aliases
   - workflow aliases
   - current route
   - role restrictions

This is a safe keyword-based selector, not a dynamic retrieval engine.

## User-facing response style

The popup may use route data internally, but normal user-facing answers should not expose raw routes by default.

- Keep routes in the structured manual for current-route matching, module lookup, tests, and future deep-link support.
- In popup answers, prefer module names and click/open language such as:
  - `Click Dashboard`
  - `Open Smart Daily`
  - `Go to Case Management`
  - `Select Documentation`
- Do not show raw route strings like `/smart-dashboard`, `/case-management`, or `/ur` unless the user explicitly asks for the route, path, or URL, or the discussion is clearly about routing behavior.

## How to update it

When new modules or routes are added:

1. Update `frontend/src/App.jsx` and nav config as usual.
2. Add or update the corresponding entry in `platform_manual.py`.
3. Add or update workflow recipes in `platform_workflows.py` if the module changes a cross-module workflow.
4. If the module introduces a new common user phrasing, add aliases and example questions.
5. Update the human-readable manual in `EMBER_USER_MANUAL.md`.
6. Add or update tests in `tests/test_ai_popup_platform_guide.py`.

## Known limitations

- No selected-client context yet in the popup path beyond route awareness.
- No dynamic sync from frontend route config into backend manual data.
- No action execution from the popup assistant unless existing backend tools already support the action.
- Role-aware guidance is limited to the role context available from auth at request time.
- Some modules include partial or upcoming behaviors; the selector relies on curated notes rather than runtime feature probing.

