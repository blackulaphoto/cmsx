# Documentation Page Layout Refactor

## Context

The Documentation / Notes & Documents Command Center page is currently a vertical stack of 7 independent sections that the user must scroll through linearly. The goal of this refactor is to collapse it into a 3-zone progressive disclosure layout where:

1. The template picker collapses after selection
2. Voice dictation is a mode toggle inside the write zone, not a separate section
3. Review tools only appear after a draft exists
4. The Company Guidance Library is moved off this page entirely
5. The Current Draft Context panel is replaced with a compact inline summary

This is a **layout and UX refactor only**. Do not change any business logic, API calls, state management, or data fetching. All existing functionality must be preserved — only the rendering structure and conditional visibility rules change.

---

## Target Page

Find the component that renders the "Notes and Documents Command Center" page. It likely lives at a path similar to one of:
- `src/pages/documentation/index.jsx`
- `src/components/documentation/DocumentationCenter.jsx`
- `src/app/documentation/page.jsx`
- `pages/documentation.jsx`

Search for the string `"Notes and Documents Command Center"` or `"Documentation Center"` to locate the right file.

---

## Section Inventory (current state)

These are the sections currently rendered on the page, in order:

| # | Section name | Current behavior |
|---|---|---|
| 1 | Hero header (stats: Templates, Client Notes, Documents, Client Linked) | Always visible |
| 2 | Template Gallery (13 cards, filter tabs, search bar) | Always fully expanded |
| 3 | Writer — "Start here" onboarding callout | Always visible |
| 4 | Writer — Selected Template display | Shows when template selected |
| 5 | Writer — Linked Client selector | Always visible |
| 6 | Writer — Case Manager Brief textarea + Generate Draft button | Always visible |
| 7 | Dictate Note — mic controls, transcript display, Generate CM Note | Always visible, separate section below the brief |
| 8 | Final Draft editor (Title, Type, draft textarea) | Always visible |
| 9 | Save Note button | Always visible |
| 10 | Review and Follow-up Tools (AI Documentation Assist, Compliance Review) | Always visible |
| 11 | Current Draft Context (read-only metadata panel) | Always visible |
| 12 | Company Guidance Library (upload form) | Always visible |
| 13 | Saved Notes (client-linked note record list) | Always visible |

---

## Required Changes

### CHANGE 1 — Template Gallery: collapse after selection

**Current behavior:** The full 13-card grid with filter tabs and search bar is always visible.

**New behavior:**
- When no template is selected, show the gallery as-is (full grid, filters, search). This is the "picker" state.
- When a template IS selected, hide the full gallery and replace it with a single compact "selected template" bar:

```
[ 📄 Weekly CM Note  ·  Client Note · Progress · Clinical ]   [ Change template × ]
```

- The "Change template" button clears the selection and returns to the full gallery state.
- The "×" button also clears the selection.
- Use existing state (whatever variable tracks `selectedTemplate`) to drive this. Do not add new state.

**Implementation notes:**
- Wrap the gallery grid in a conditional: `{!selectedTemplate && <TemplateGallery ... />}`
- Add a new `SelectedTemplateBadge` inline component (can be defined in the same file) that renders the compact bar when `selectedTemplate` is truthy.
- The badge should display: template title, template tags, and a "Change template" button that calls the existing clear/reset handler.

---

### CHANGE 2 — Voice dictation becomes a mode toggle inside the write zone

**Current behavior:** The "Dictate Note" section (mic button, transcript area, "Generate CM Note" button) is a separate full-width section rendered *below* the Case Manager Brief section, after the "Generate Draft" button.

**New behavior:** 
- Add an input mode toggle at the top of the write zone (above the Case Manager Brief / Linked Client area).
- The toggle has two states: `"type"` (default) and `"dictate"`.
- When mode is `"type"`: show the Case Manager Brief textarea and Generate Draft button. Hide the Dictate Note section.
- When mode is `"dictate"`: hide the Case Manager Brief textarea. Show the mic controls (Start Recording button, Use Transcript in Brief button, Generate CM Note button) and the transcript display area inline, in the same visual container as the write zone.
- Remove the Dictate Note section from its current standalone position entirely.
- The "Use Transcript in Brief" button should switch the mode back to `"type"` after copying the transcript into the brief textarea (preserve existing logic).

**Toggle UI:**
```
[ ✏ Type ]  [ 🎙 Dictate ]
```
- Two buttons styled as a segmented control (pill-shaped, active state filled, inactive state outlined).
- Place this toggle directly above the Linked Client selector row, inside the Writer card/section.

**State:**
```js
const [inputMode, setInputMode] = useState('type'); // 'type' | 'dictate'
```

---

### CHANGE 3 — Review tools: only show after draft exists

**Current behavior:** The "Review and Follow-up Tools" section (AI Documentation Assist textarea, Draft Note button, Compliance Review button) is always visible, even before any draft has been generated.

**New behavior:**
- Hide this entire section when the draft is empty.
- Show it only when the final draft textarea has content (i.e., `finalDraft.trim().length > 0`).
- No animation required. A simple conditional render is fine.
- Optionally add a subtle divider and label above it: `"Draft review tools"` in muted text.

**Implementation:**
```jsx
{finalDraft && finalDraft.trim().length > 0 && (
  <ReviewToolsSection ... />
)}
```

Use whatever the existing state variable name is for the final draft content.

---

### CHANGE 4 — Current Draft Context panel: replace with inline summary

**Current behavior:** A full-width card section labeled "Current Draft Context" displays 4 read-only rows: Template, Template source, Save target, Client, Editor mode.

**New behavior:**
- Remove the full "Current Draft Context" section card entirely.
- Add a single compact metadata line directly below the "Save Note" button:

```
Template: Weekly CM Note  ·  Saving to: Client note record  ·  Client: AIFallback Client
```

- Style: 12px, `color: var(--muted)` or equivalent muted text color in your system. No card, no border, no heading.
- Only show this line when a template is selected and/or a client is linked. If neither is set, omit it entirely.

---

### CHANGE 5 — Company Guidance Library: move to Settings

**Current behavior:** The full Company Guidance Library upload form (category dropdown, description textarea, file picker, Upload button) is rendered on this page.

**New behavior:**
- Remove the Company Guidance Library section from this page entirely.
- Replace it with a single text link, placed just above the Saved Notes section:

```
⚙ Manage AI style guides and company guidance →
```

- This link should navigate to wherever the Guidance Library currently lives or will live (use the existing route if one exists, otherwise use `"/settings/guidance"` as a placeholder href).
- Style as a small muted text link, not a button.

---

### CHANGE 6 — Section order after refactor

After all changes above, the page should render in this order, top to bottom:

1. **Hero header** — stats row (unchanged)
2. **Zone 1: Template picker** — either full gallery (no selection) OR compact selected-template badge
3. **Zone 2: Write zone** — single card/section containing:
   a. Input mode toggle (Type / Dictate)
   b. Linked Client selector
   c. *If mode === 'type':* Case Manager Brief textarea + Generate Draft button
   d. *If mode === 'dictate':* Mic controls + transcript area + Generate CM Note button
   e. Horizontal rule / visual divider
   f. Final Draft editor (Title field, Type dropdown, draft textarea)
   g. Save Note button
   h. Compact metadata summary line (draft context)
   i. *If draft exists:* Review tools (AI Documentation Assist, Compliance Review)
4. **Guidance Library link** — single text link
5. **Saved Notes** — client note record list (unchanged)

---

## What NOT to change

- Do not change any state management logic, only conditional rendering.
- Do not change any API call sites, action handlers, or data fetching.
- Do not change the Template Gallery component internals — only wrap it in a conditional.
- Do not change the Dictate Note / voice logic — only move where it renders and make it conditionally visible.
- Do not change the Saved Notes section.
- Do not change the Hero stats header.
- Do not restyle any existing components. This is a structural/layout change, not a visual redesign.
- Do not add new dependencies.

---

## Acceptance criteria

- [ ] Selecting a template collapses the full gallery to the compact badge. Clicking "Change template" restores the gallery.
- [ ] The "Dictate" toggle shows mic controls in-place of the brief textarea. "Type" toggle shows the textarea. No duplicate sections exist.
- [ ] Review tools are not visible on page load. They appear after draft content exists.
- [ ] The Current Draft Context card section is gone. A one-line muted summary appears below Save.
- [ ] The Company Guidance Library upload form is not on this page. A text link to settings replaces it.
- [ ] All existing functionality (generate draft, save note, voice recording, compliance review, AI assist, template selection) still works.
- [ ] No console errors introduced.

---

## Notes for Codex

- Search for component boundaries by looking for section headings: `"Template Gallery"`, `"Writer"`, `"Dictate Note"`, `"Review and follow-up tools"`, `"Current Draft Context"`, `"Company Guidance Library"`, `"Saved Notes"`.
- The input mode toggle state (`inputMode`) is new — add it locally in the parent page component or the Writer section component, whichever owns the brief textarea and the dictate section today.
- If the Dictate Note section is a separate imported component, keep it as-is and just move where it's rendered (inside the write zone, conditionally on `inputMode === 'dictate'`).
- If any section is already conditionally rendered, preserve that logic and layer the new conditions on top with `&&`.
